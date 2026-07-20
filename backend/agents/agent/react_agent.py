"""LangGraph ReAct agent using the model's native tool-calling protocol."""

from __future__ import annotations

import asyncio
import os

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from backend.agents.agent.get_llm import get_llm
from backend.agents.agent.tools import GraphState
from backend.agents.skills import get_skill_list_prompt
from backend.agents.tools import TOOLS, TOOL_MAP, get_tool_prompt
from backend.agents.tools.result import ToolExecutionError, serialize_tool_result
from backend.middleware.logging import get_logger

logger = get_logger(__name__)
TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "60"))


_REACT_SYSTEM_PROMPT = """# 角色
你是智学伴的 ReAct 决策 Agent。请根据用户输入和当前工具调用上下文，自主决定调用工具或直接回答。

# 可用工具
只能调用系统绑定的工具，禁止编造不存在的工具。工具说明如下：

""" + get_tool_prompt() + """

# 可用 Skill
Skill 是按需加载的程序化知识。当用户请求命中某个 Skill 的触发场景时，先调用 load_skill_tool 加载它，再根据加载结果决定后续动作。

""" + get_skill_list_prompt() + """

# 规则
1. 查询业务数据或执行具体能力时，必须调用工具，不得编造工具结果。
2. 使用模型原生 Function Calling 选择工具，不要用文本、JSON 或 Markdown 模拟工具调用。
3. 每轮最多调用一个工具；如果仍需其他工具，等待真实工具结果后再决定下一步。
4. 必须结合前序 ToolMessage 的结果继续决策。
   ToolMessage 是JSON对象：success表示是否成功，code表示结果码，message是说明，data是数据。
   success=false时，根据code决定修正参数、改用其他工具或向用户说明失败，不得把失败内容当成正常数据。
5. 命中 Skill 触发场景时，先调用 load_skill_tool，再按加载结果行动。
6. 信息充分时直接用简洁、易懂的中文回答用户。
7. 工具和自身能力均无法处理时，明确说明“我暂时无法处理这个问题”。
"""

REACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _REACT_SYSTEM_PROMPT),
    ("user", "{user_input}"),
    MessagesPlaceholder(variable_name="messages"),
])


def react_think_node(state: GraphState) -> dict:
    """Use native tool calls to choose one action or produce the final answer."""
    round_number = state["round"] + 1
    try:
        llm = get_llm().bind_tools(TOOLS)
        chain = REACT_PROMPT | llm
        response = chain.invoke({
            "user_input": state["user_input"],
            "messages": state["messages"],
        })
    except Exception:
        logger.exception("Agent model invocation failed in round %s", round_number)
        fallback = "智能学习服务暂时不可用，请稍后重试。"
        return {
            "thought": "模型调用失败",
            "action": "",
            "action_args": {},
            "tool_call_id": "",
            "round": round_number,
            "final_result": fallback,
            "messages": [AIMessage(content=fallback)],
        }

    tool_calls = response.tool_calls or []

    if tool_calls:
        # The workflow deliberately executes at most one tool per round.
        tool_call = tool_calls[0]
        if (
            not isinstance(tool_call.get("name"), str)
            or not tool_call.get("name")
            or not isinstance(tool_call.get("args", {}), dict)
            or not tool_call.get("id")
        ):
            logger.error("Invalid native tool call: %r", tool_call)
            fallback = "工具调用格式无效，请重新描述你的学习问题。"
            return {
                "thought": "工具调用格式无效",
                "action": "",
                "action_args": {},
                "tool_call_id": "",
                "round": round_number,
                "final_result": fallback,
                "messages": [AIMessage(content=fallback)],
            }

        if round_number >= 5:
            fallback = "处理步骤已达到上限，请缩小问题范围后重试。"
            return {
                "thought": "已达到最大工具调用轮数",
                "action": "",
                "action_args": {},
                "tool_call_id": "",
                "round": round_number,
                "final_result": fallback,
                "messages": [AIMessage(content=fallback)],
            }

        # Keep the stored AIMessage protocol-consistent if a provider ignores
        # the one-tool-per-round instruction and returns parallel calls.
        response.tool_calls = [tool_call]
        action = tool_call["name"]
        action_args = tool_call.get("args", {})
        tool_call_id = tool_call["id"]
        final_result = ""
        status = f"正在调用工具：{action}"
    else:
        action = ""
        action_args = {}
        tool_call_id = ""
        final_result = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        status = "回答已生成"

    logger.info("Agent round: %s", round_number)
    logger.info("Agent tool: %s", action or "none")
    logger.debug("Agent tool args: %s", action_args)

    return {
        "thought": status,
        "action": action,
        "action_args": action_args,
        "tool_call_id": tool_call_id,
        "round": round_number,
        "final_result": final_result,
        # add_messages reducer appends the AIMessage to the graph history.
        "messages": [response],
    }


async def tool_exec_node(state: GraphState) -> dict:
    """Execute the selected tool and append a protocol-correct ToolMessage."""
    func_name = state["action"]
    tool = TOOL_MAP.get(func_name)
    try:
        if tool is None:
            raise ToolExecutionError("UNKNOWN_TOOL", f"系统不存在工具：{func_name}")

        args_schema = getattr(tool, "args_schema", None)
        args = dict(state["action_args"])
        if args_schema is not None:
            args = args_schema.model_validate(args).model_dump(exclude_none=True)

        # Identity-bound parameters never come from model-generated arguments.
        if func_name == "query_memory_tool":
            args["user_id"] = state["user_id"]
            args["session_id"] = state["session_id"]
        if func_name in (
            "user_profile_save_tool",
            "user_profile_query_tool",
            "user_profile_delete_tool",
        ):
            args["user_id"] = state["user_id"]

        result = await asyncio.wait_for(
            tool._arun(**args),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
        if hasattr(result, "content"):
            result = result.content

        content = serialize_tool_result(
            tool=func_name,
            success=True,
            code="OK",
            message="工具执行成功",
            data=result,
        )
    except ValidationError as exc:
        content = serialize_tool_result(
            tool=func_name,
            success=False,
            code="INVALID_TOOL_ARGUMENTS",
            message="工具参数不符合要求",
            data={"errors": exc.errors(include_url=False)},
        )
    except ToolExecutionError as exc:
        content = serialize_tool_result(
            tool=func_name,
            success=False,
            code=exc.code,
            message=exc.message,
        )
    except TimeoutError:
        logger.warning("Tool %s timed out after %ss", func_name, TOOL_TIMEOUT_SECONDS)
        content = serialize_tool_result(
            tool=func_name,
            success=False,
            code="TOOL_TIMEOUT",
            message="工具执行超时，请稍后重试",
        )
    except Exception:
        logger.exception("Unhandled error while executing tool %s", func_name)
        content = serialize_tool_result(
            tool=func_name,
            success=False,
            code="TOOL_EXECUTION_FAILED",
            message="工具执行失败，请稍后重试",
        )

    return {
        "messages": [ToolMessage(
            content=content,
            tool_call_id=state["tool_call_id"],
            name=func_name,
        )]
    }


def should_continue(state: GraphState) -> str:
    """Continue while the model selected a tool and the round limit permits it."""
    if state["action"] and state["round"] < 5:
        return "execute_tool"
    return END


workflow = StateGraph(GraphState)
workflow.add_node("react_think", react_think_node)
workflow.add_node("execute_tool", tool_exec_node)
workflow.set_entry_point("react_think")
workflow.add_conditional_edges("react_think", should_continue)
workflow.add_edge("execute_tool", "react_think")

_compiled_app = workflow.compile()

def get_app():
    """Return the process-wide compiled graph."""
    return _compiled_app
