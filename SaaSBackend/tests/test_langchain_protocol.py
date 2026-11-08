"""Exercise the real LangChain + OpenAI SDK against an offline HTTP transport."""
import asyncio
import json

import httpx2
import openai
import pytest

from agents.agent_orchestrator import TechnicalAgent, AgentOrchestrator, AgentType, Request
from agents.tools import AgentToolSpec
from core.intent_recognizer import IntentCategory, UrgencyLevel
from core.llm_client import LangChainClient


def response(message, reason="stop"):
    return {"id": "chatcmpl-test", "object": "chat.completion", "created": 1,
            "model": "deepseek-v4-pro", "choices": [{"index": 0, "message": message,
            "finish_reason": reason}], "usage": {"prompt_tokens": 20, "completion_tokens": 10,
            "total_tokens": 30}}


def tool_call(name="lookup_error_code", args=None, id="call-1"):
    return {"role": "assistant", "content": None, "reasoning_content": "provider-test-state",
            "tool_calls": [{"id": id, "type": "function", "function": {"name": name,
            "arguments": json.dumps({"error_code": "401"} if args is None else args)}}]}


async def setup_client(replies, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_THINKING", "enabled")
    calls = []
    def handle(request):
        calls.append({"path": request.url.path, "body": json.loads(request.content)})
        item = replies[min(len(calls)-1, len(replies)-1)]
        return httpx2.Response(item[0], json=item[1]) if isinstance(item, tuple) else httpx2.Response(200,json=item)
    gateway = LangChainClient("offline-test-key", "https://unit.test/v1")
    model = gateway.model_for("deepseek-v4-pro", max_tokens=TechnicalAgent.profile.max_tokens,
                               temperature=TechnicalAgent.profile.temperature)
    await model.root_async_client.close()
    model.root_async_client = openai.AsyncOpenAI(api_key="offline-test-key", base_url=gateway.base_url,
        max_retries=0, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle)))
    model.async_client = model.root_async_client.chat.completions
    return gateway, calls


def request():
    return Request(message="API 登录返回 401", user_id="u", conv_id="c",
        intent=IntentCategory.TECHNICAL_LOGIN, intent_group="technical", urgency=UrgencyLevel.LOW,
        intent_confidence=.9, entities={"error_code": ["401"]})


@pytest.mark.asyncio
async def test_openai_wire_tools_and_reasoning_roundtrip(monkeypatch):
    client, calls = await setup_client([response(tool_call(), "tool_calls"),
        response({"role": "assistant", "content": "请核查认证和 Token 有效期。"})],monkeypatch)
    try:
        result = await TechnicalAgent(client,"deepseek-v4-pro").handle(request())
        assert result.status == "success", result
        assert result.tools_used == ["lookup_error_code"]
        assert result.tool_traces[0]["tool_use_id"] == "call-1"
        assert all(c["path"] == "/v1/chat/completions" for c in calls)
        assert calls[0]["body"]["thinking"] == {"type":"enabled"}
        assert calls[0]["body"]["model"] == "deepseek-v4-pro"
        assert "max_tokens" in calls[0]["body"]
        assert "max_completion_tokens" not in calls[0]["body"]
        history = calls[1]["body"]["messages"]
        assert next(m for m in history if m.get("tool_calls"))["reasoning_content"] == "provider-test-state"
        assert next(m for m in history if m["role"] == "tool")["tool_call_id"] == "call-1"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_unregistered_tool_is_rejected_and_traced(monkeypatch):
    client, calls = await setup_client([response(tool_call("issue_refund", {}), "tool_calls"),
        response({"role":"assistant","content":"需要人工核验。"})],monkeypatch)
    try:
        result = await TechnicalAgent(client,"deepseek-v4-pro").handle(request())
        assert result.status == "success"
        assert result.tools_used == []
        assert result.tool_traces[0]["success"] is False
        assert "白名单" in result.tool_traces[0]["error"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_truncated_tool_response_never_executes_a_write(monkeypatch):
    client, calls = await setup_client([response(tool_call("write", {}), "length")],monkeypatch)
    seen = []
    agent = TechnicalAgent(client,"deepseek-v4-pro")
    agent.set_shared_tools({"write":AgentToolSpec("write","test only",{"type":"object","properties":{}},
        lambda req,args: seen.append(True), retry_safe=False)})
    try:
        result = await agent.handle(request())
        assert result.status == "failed" and not seen
        assert len(calls) == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_model_request_budget_remains_three(monkeypatch):
    client, calls = await setup_client([response(tool_call(),"tool_calls")],monkeypatch)
    try:
        result = await TechnicalAgent(client,"deepseek-v4-pro").handle(request())
        assert result.status == "failed"
        assert len(calls) == 3
        assert len(result.tool_traces) == 3
        assert all(t["tool_use_id"] == "call-1" for t in result.tool_traces)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_auth_error_has_no_hidden_sdk_retry(monkeypatch):
    client, calls = await setup_client([(401,{"error":{"message":"bad key","type":"authentication_error"}})],monkeypatch)
    try:
        result = await TechnicalAgent(client,"deepseek-v4-pro").handle(request())
        assert result.status == "failed" and len(calls)==1
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("finish,expected", [("stop","end_turn"),("length","max_tokens")])
async def test_auxiliary_tasks_preserve_text_and_completion_state(monkeypatch, finish, expected):
    client, calls = await setup_client([response({"role":"assistant","content":'{"ok":true}'},finish)],monkeypatch)
    try:
        result = await client.messages.create(model="deepseek-v4-pro", max_tokens=TechnicalAgent.profile.max_tokens,
            temperature=TechnicalAgent.profile.temperature, system="Return JSON",
            messages=[{"role":"user","content":"test"}])
        assert result.content[0]["text"] == '{"ok":true}'
        assert result.stop_reason == expected
        assert calls[0]["body"]["messages"][0]["role"] == "system"
    finally:
        await client.close()


@pytest.mark.parametrize("intent,message,expected",[
    (IntentCategory.QUERY,"这个功能怎么用",AgentType.GENERAL),
    (IntentCategory.QUERY,"新用户使用引导",AgentType.GENERAL),
    (IntentCategory.TECHNICAL,"API 对接问题",AgentType.TECHNICAL),
    (IntentCategory.ACCOUNT,"企业账户使用说明",AgentType.GENERAL),
    (IntentCategory.BILLING,"订阅续费说明",AgentType.BILLING),
])
def test_saas_requests_use_existing_agents(intent,message,expected):
    orch=AgentOrchestrator(api_key="offline-test-key",model="deepseek-v4-pro")
    req=request()
    req.intent, req.message=intent,message
    assert orch._route_decision(req).primary_agent == expected
    assert set(AgentType) == {AgentType.GENERAL,AgentType.TECHNICAL,AgentType.BILLING,AgentType.ESCALATION}
