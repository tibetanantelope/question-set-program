import asyncio
from typing import Type, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from backend.agents.memory.short_term_memory import get_short_term_memory
from backend.agents.tools.result import ToolExecutionError


class QueryMemoryInput(BaseModel):
    limit: int = Field(default=5, ge=1, le=20, description="返回的记忆条数")


class QueryMemoryTool(BaseTool):
    name: str = "query_memory_tool"
    description: str = "查询当前用户的历史对话记忆，用于了解用户过去的问题、偏好或上下文"
    args_schema: Type[BaseModel] = QueryMemoryInput

    def _run(self, user_id: Optional[int] = None, session_id: Optional[int] = None, limit: int = 5) -> str:
        """同步执行记忆查询（委托给异步版本）"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._arun(user_id=user_id, session_id=session_id, limit=limit))
        except RuntimeError:
            raise ToolExecutionError("SYNC_TOOL_UNAVAILABLE", "当前环境不能同步查询记忆")

    async def _arun(self, user_id: Optional[int] = None, session_id: Optional[int] = None, limit: int = 5) -> str:
        """异步执行记忆查询"""
        if user_id is None or session_id is None:
            raise ToolExecutionError("MISSING_USER_CONTEXT", "缺少当前用户或会话身份")
        try:
            memory = await get_short_term_memory()
            memories = await memory.get_latest_memories(user_id, session_id, limit)

            if not memories:
                return "【记忆查询】未找到相关记忆"

            lines = []
            for i, mem in enumerate(memories, 1):
                memory_content = mem.get('memory', {})
                user_content = memory_content.get('user_memory', '')
                model_content = memory_content.get('model_memory', '')
                timestamp = mem.get('timestamp', '')
                lines.append(f"{i}. 时间: {timestamp}\n用户: {user_content}\n模型: {model_content}")

            return "【记忆查询】找到以下记忆：\n" + "\n".join(lines)
        except Exception as e:
            raise ToolExecutionError("MEMORY_QUERY_FAILED", "记忆查询失败") from e
