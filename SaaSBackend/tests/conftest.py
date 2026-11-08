"""Adapt the original regression fixtures at the test boundary.

Old fixtures retain their recorded calls and failure schedules. They run through
the real LangChain agent graph; network contracts are tested separately with an
httpx mock transport and the real OpenAI SDK.
"""
import json

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class RecordedFixtureModel(BaseChatModel):
    client: object
    bound_tools: list = []

    @property
    def _llm_type(self):
        return "recorded-regression-fixture"

    def bind_tools(self, tools, **kwargs):
        from langchain_core.utils.function_calling import convert_to_openai_tool
        return self.model_copy(update={"bound_tools": [convert_to_openai_tool(t) for t in tools]})

    def _generate(self, messages, **kwargs):
        raise NotImplementedError("Async regression fixture")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        converted = []
        system = None
        for m in messages:
            if m.type == "system":
                system = m.content
            elif m.type == "tool":
                converted.append({"role": "user", "content": [{"type": "tool_result",
                    "tool_use_id": m.tool_call_id, "content": m.content}]})
            else:
                converted.append({"role": "assistant" if m.type == "ai" else "user", "content": m.content})
        params = dict(messages=converted, system=system, tools=[dict(name=t["function"]["name"],
            description=t["function"].get("description", ""),
            input_schema=t["function"]["parameters"]) for t in self.bound_tools])
        raw = await self.client.messages.create(**params)
        def value(block, name, default=None):
            return block.get(name, default) if isinstance(block, dict) else getattr(block, name, default)
        content = raw.content or []
        calls = [dict(name=value(b,"name"), args=value(b,"input",{}), id=value(b,"id"),type="tool_call")
                 for b in content if value(b,"type") == "tool_use"]
        text = "\n".join(value(b,"text","") for b in content if value(b,"type") == "text")
        reason = "length" if getattr(raw,"stop_reason",None) == "max_tokens" else "tool_calls" if calls else "stop"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text, tool_calls=calls,
            response_metadata={"finish_reason":reason}))])


@pytest.fixture(autouse=True)
def adapt_recorded_agent_fixtures(monkeypatch):
    import agents.langchain_runtime as runtime
    original = runtime.agent_model
    def model(client, name, **kwargs):
        if hasattr(client, "model_for"):
            return original(client, name, **kwargs)
        return RecordedFixtureModel(client=client)
    monkeypatch.setattr(runtime,"agent_model",model)
