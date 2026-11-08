# 阅读导航：统一模型接入层，负责 LangChain 模型实例与 OpenAI 兼容协议适配。
# 普通 Agent 使用原生模型；意图、摘要、改写、重排和 Judge 使用 complete 文本任务接口。

"""Shared LangChain model gateway. Network protocol: OpenAI Chat Completions.

The small text-completion facade keeps auxiliary tasks independent of provider
message classes. Agent execution uses the native model with create_agent.
"""
import os
from types import SimpleNamespace

from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from core.llm_utils import extract_text_content


class CompatibleDeepSeek(ChatDeepSeek):
    """Preserve DeepSeek reasoning across tool turns on the OpenAI wire format."""

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        # DeepSeek 的思考字段需要随工具往返保留；丢失它可能导致后续模型请求格式不完整。
        # 这里只补供应商协议差异，不改变角色提示词、路由或业务规则。
        messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        for original, serialized in zip(messages, payload["messages"]):
            if original.type == "ai" and "reasoning_content" in original.additional_kwargs:
                serialized["reasoning_content"] = original.additional_kwargs["reasoning_content"]
        # DeepSeek documents max_tokens, rather than OpenAI's renamed parameter.
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload.pop("max_completion_tokens")
        return payload


class LangChainClient:
    def __init__(self, api_key, base_url=None, max_retries=0):
        self.api_key = api_key
        self.base_url = base_url or "https://api.deepseek.com"
        # 默认关闭 SDK 隐藏重试，避免一次业务调用在底层重复发送而绕过上层预算。
        self.max_retries = max_retries
        self._models = {}
        self.messages = SimpleNamespace(create=self.complete)

    async def close(self):
        for model in self._models.values():
            if model.root_async_client is not None:
                await model.root_async_client.close()
            if model.root_client is not None:
                model.root_client.close()
        self._models.clear()

    def model_for(self, model, *, max_tokens=1024, temperature=0.0):
        # 按模型名、token 预算和温度缓存实例，同一配置复用连接资源。
        # DeepSeek 走专用适配器，其他模型走 ChatOpenAI；两者均使用 Chat Completions 协议。
        key = (model, max_tokens, temperature)
        if key not in self._models:
            kwargs = dict(model=model, api_key=self.api_key, base_url=self.base_url,
                          max_tokens=max_tokens, temperature=temperature,
                          max_retries=self.max_retries, timeout=45)
            if "deepseek" in model.lower():
                thinking = os.getenv("DEEPSEEK_THINKING", "disabled").strip()
                if thinking not in {"enabled", "disabled"}:
                    raise ValueError("DEEPSEEK_THINKING 必须是 enabled 或 disabled")
                kwargs["extra_body"] = {"thinking": {"type": thinking}}
                self._models[key] = CompatibleDeepSeek(**kwargs)
            else:
                self._models[key] = ChatOpenAI(**kwargs, use_responses_api=False)
        return self._models[key]

    async def complete(self, *, model, messages, max_tokens=1024, temperature=0.0, system=None):
        # 这是辅助文本任务的应用内兼容外观，不是 Anthropic 网络协议。
        # 内部仍由 LangChain ainvoke 执行；把返回内容统一成旧辅助模块能读取的文本结构。
        prompt = [SystemMessage(content=system)] if system else []
        prompt.extend(messages)
        reply = await self.model_for(model, max_tokens=max_tokens, temperature=temperature).ainvoke(prompt)
        reason = reply.response_metadata.get("finish_reason")
        if reason not in {"stop", "length"}:
            raise ValueError(f"辅助模型任务未完整结束: {reason}")
        return SimpleNamespace(content=[{"type": "text", "text": extract_text_content(reply.content)}],
                               stop_reason="max_tokens" if reason == "length" else "end_turn")


def agent_model(client, model, *, max_tokens, temperature):
    return client.model_for(model, max_tokens=max_tokens, temperature=temperature)
