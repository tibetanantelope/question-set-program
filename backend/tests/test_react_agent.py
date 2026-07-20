import os
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

# Tool imports reach the SQLAlchemy model module during collection.
os.environ.setdefault(
    "SQL_DATABASE_URL",
    "mysql+asyncmy://test:test@127.0.0.1:3306/test",
)

from backend.agents.agent import react_agent


def _state(**overrides):
    state = {
        "user_input": "帮我生成一道方程练习",
        "user_id": 7,
        "session_id": 11,
        "thought": "",
        "action": "",
        "action_args": {},
        "tool_call_id": "",
        "messages": [],
        "round": 0,
        "final_result": "",
    }
    state.update(overrides)
    return state


def test_react_node_reads_native_tool_call(monkeypatch):
    response = AIMessage(
        content="",
        tool_calls=[{
            "name": "common_tool",
            "args": {"query": "测试"},
            "id": "call-123",
            "type": "tool_call",
        }],
    )

    class FakeModel:
        def bind_tools(self, _tools):
            return RunnableLambda(lambda _input: response)

    monkeypatch.setattr(react_agent, "get_llm", lambda: FakeModel())
    result = react_agent.react_think_node(_state())

    assert result["action"] == "common_tool"
    assert result["action_args"] == {"query": "测试"}
    assert result["tool_call_id"] == "call-123"
    assert result["final_result"] == ""
    assert result["messages"] == [response]


@pytest.mark.asyncio
async def test_tool_message_matches_native_call_id_and_injects_identity(monkeypatch):
    captured = {}

    class FakeTool:
        async def _arun(self, **kwargs):
            captured.update(kwargs)
            return "memory result"

    monkeypatch.setitem(react_agent.TOOL_MAP, "query_memory_tool", FakeTool())
    result = await react_agent.tool_exec_node(_state(
        action="query_memory_tool",
        action_args={"limit": 3, "user_id": 999},
        tool_call_id="call-456",
    ))

    assert captured == {"limit": 3, "user_id": 7, "session_id": 11}
    message = result["messages"][0]
    assert isinstance(message, ToolMessage)
    assert message.tool_call_id == "call-456"
    assert message.name == "query_memory_tool"
    payload = json.loads(message.content)
    assert payload == {
        "success": True,
        "code": "OK",
        "message": "工具执行成功",
        "data": "memory result",
        "tool": "query_memory_tool",
    }


@pytest.mark.asyncio
async def test_invalid_tool_arguments_return_structured_error(monkeypatch):
    from backend.agents.tools.common_tool import CommonTool

    monkeypatch.setitem(react_agent.TOOL_MAP, "common_tool", CommonTool())
    result = await react_agent.tool_exec_node(_state(
        action="common_tool",
        action_args={},
        tool_call_id="call-invalid",
    ))

    payload = json.loads(result["messages"][0].content)
    assert payload["success"] is False
    assert payload["code"] == "INVALID_TOOL_ARGUMENTS"
    assert payload["tool"] == "common_tool"


def test_model_failure_returns_safe_final_answer(monkeypatch):
    class BrokenModel:
        def bind_tools(self, _tools):
            return RunnableLambda(lambda _input: (_ for _ in ()).throw(RuntimeError("secret")))

    monkeypatch.setattr(react_agent, "get_llm", lambda: BrokenModel())
    result = react_agent.react_think_node(_state())

    assert result["action"] == ""
    assert result["final_result"] == "智能学习服务暂时不可用，请稍后重试。"
    assert "secret" not in result["final_result"]
