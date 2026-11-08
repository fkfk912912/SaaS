# 阅读导航：单个模型 Agent 的执行入口，包含模型预算、工具包装、消息构造与结果检查。
# create_agent 运行模型→工具→观察结果的循环；这里不负责跨角色的主辅路由。

"""Request-scoped LangChain agents with the existing business execution guards."""
import asyncio
import inspect
import json
import time
from contextvars import ContextVar

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from core.llm_client import agent_model
from core.llm_utils import extract_text_content


async def run_agent(agent, req):
    # 每次请求单独创建工具轨迹、锁和中间件，避免不同用户或主辅角色互相串状态。
    # 角色工具集合由 get_tools 给出，模型不能自行扩展权限。
    from agents.agent_orchestrator import AgentCallError, AgentCallResult, _env_float

    tools_used, traces = [], []
    tools = agent.get_tools()
    # The old loop executes tools in order. Keep write guards and traces serial
    # even when a provider returns more than one tool call in a single response.
    tool_lock = asyncio.Lock()
    active_call = ContextVar("active_tool_call", default=None)

    class ExecutionBudget(AgentMiddleware):
        calls = 0

        async def awrap_model_call(self, request, handler):
            # 最多三次指模型请求次数，包含最后一次生成答案；不是最多三个工具。
            # 一轮模型输出可能提出多个工具调用，但截断或参数无效时不能执行这些操作。
            if self.calls >= 3:
                raise AgentCallError(f"{agent.agent_type.value} 工具调用超过最大轮数", tools_used, traces)
            self.calls += 1
            result = await asyncio.wait_for(handler(request),
                timeout=max(1, _env_float("ECHOMIND_LLM_TIMEOUT_S", 15)))
            for message in result.result:
                if not isinstance(message, AIMessage):
                    continue
                finish = message.response_metadata.get("finish_reason")
                if message.invalid_tool_calls:
                    raise ValueError("模型返回无效的工具参数")
                if finish not in {"stop", "tool_calls", "length"}:
                    raise ValueError(f"模型响应未正常结束: {finish}")
                if message.tool_calls and finish != "tool_calls":
                    raise ValueError("工具调用响应不完整，停止执行")
            return result

        async def awrap_tool_call(self, request, handler):
            # 把模型的 tool_call_id 放入请求上下文，随后用于关联工具结果与追踪记录。
            # 白名单拒绝由程序执行，并把错误作为 ToolMessage 交回模型。
            call = request.tool_call
            token = active_call.set(call["id"])
            try:
                if call["name"] not in tools:
                    error = f"工具不在 {agent.agent_type.value} Agent 白名单中"
                    traces.append({"agent_type": agent.agent_type.value, "tool_name": call["name"],
                        "tool_use_id": call["id"], "input": call["args"], "success": False,
                        "result_success": False, "latency_ms": 0, "cached": False, "reranked": False,
                        "error": error, "source": "local", "mcp_server": None, "mcp_tool": None,
                        "retry_safe": True})
                    return ToolMessage(content=json.dumps({"success": False, "error": error}, ensure_ascii=False),
                                       tool_call_id=call["id"], name=call["name"], status="error")
                return await handler(request)
            finally:
                active_call.reset(token)

    def make_tool(spec):
        async def execute(**args):
            # 同一 Agent 本次请求内的工具串行执行，使副作用保护、调用顺序和轨迹保持一致。
            # 参数校验完成后，非重试安全工具先记执行标记，再运行真实 handler。
            async with tool_lock:
                start = time.monotonic()
                call_success, result_success, error = True, None, ""
                try:
                    agent._validate_tool_input(spec, args)
                    if not spec.retry_safe:
                        operation = json.dumps([spec.name, args], sort_keys=True, ensure_ascii=True)
                        if operation in req.unsafe_tool_calls:
                            raise ValueError("同一请求不能重复执行相同的副作用工具操作，请先核验结果")
                        req.unsafe_tool_calls.add(operation)
                    req.tool_attempts.append({"tool_name": spec.name, "retry_safe": spec.retry_safe})
                    if not spec.retry_safe and req.before_unsafe_tool is not None:
                        await req.before_unsafe_tool(spec.name)
                    result = spec.handler(req, args)
                    if inspect.isawaitable(result):
                        result = await result
                    # call_success 表示 handler 未抛异常；result_success 记录工具自报的业务结果，两者不等价。
                    tools_used.append(spec.name)
                    if isinstance(result, dict) and "success" in result:
                        result_success = bool(result["success"])
                except Exception as ex:
                    call_success, error = False, str(ex)
                    result = {"success": False, "error": error}
                if isinstance(result, dict) and not error:
                    error = str(result.get("error", "") or "")
                traces.append({
                    "agent_type": agent.agent_type.value, "tool_name": spec.name,
                    "tool_use_id": active_call.get(), "input": dict(args), "success": call_success,
                    "result_success": result_success,
                    "latency_ms": round((time.monotonic() - start) * 1000, 1),
                    "cached": bool(result.get("cached")) if isinstance(result, dict) else False,
                    "reranked": bool(result.get("reranked")) if isinstance(result, dict) else False,
                    "error": error,
                    "source": result.get("source", "local") if isinstance(result, dict) else "local",
                    "mcp_server": result.get("mcp_server") if isinstance(result, dict) else None,
                    "mcp_tool": result.get("mcp_tool") if isinstance(result, dict) else None,
                    "retry_safe": spec.retry_safe,
                })
                return json.dumps(result, ensure_ascii=False)

        return StructuredTool.from_function(name=spec.name, description=spec.description,
            args_schema=spec.input_schema, coroutine=execute)

    messages = []
    for label, text in (("背景信息", req.context),
                        ("结构化实体", json.dumps(req.entities, ensure_ascii=False) if req.entities else ""),
                        ("角色输入契约", agent._build_role_packet(req))):
        if text:
            messages.extend([HumanMessage(content=f"[{label}]\n{text}"),
                             AIMessage(content="好的，我会结合这些信息处理。")])
    messages.append(HumanMessage(content=req.message.encode("utf-8", errors="ignore").decode("utf-8")))
    try:
        model = agent_model(agent._client, agent._model, max_tokens=agent.profile.max_tokens,
                            temperature=agent.profile.temperature)
        graph = create_agent(model=model, tools=[make_tool(spec) for spec in tools.values()],
                             system_prompt=agent._build_system_prompt(req), middleware=[ExecutionBudget()])
        # 12 是图执行步数限制；上面的中间件另外限制三次模型请求，两个预算并不等价。
        # 没有额外启用图的持久化记忆，整轮历史仍由 HTTP 入口统一提交到 Redis。
        state = await graph.ainvoke({"messages": messages}, config={"recursion_limit": 12})
        final = state["messages"][-1]
        content = extract_text_content(final.content).strip()
        if not isinstance(final, AIMessage) or final.tool_calls or not content:
            raise ValueError("模型未返回有效回复")
        return AgentCallResult(content=content, tools_used=tools_used, tool_traces=traces,
            status="partial" if final.response_metadata.get("finish_reason") == "length" else "success")
    except AgentCallError:
        raise
    except Exception as ex:
        raise AgentCallError(str(ex), tools_used, traces) from ex
