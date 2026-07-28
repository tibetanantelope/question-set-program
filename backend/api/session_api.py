"""成员一：会话短期记忆管理 API 路由 (/sessions)"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.agents.memory.short_term_memory import get_short_term_memory, ShortTermMemory

session_router = APIRouter(prefix='/sessions', tags=['会话管理'])


@session_router.delete('/{session_id}/memory')
async def clear_session_memory(
        session_id: int,
        user: User = Depends(get_current_user),
        memory: ShortTermMemory = Depends(get_short_term_memory),
):
    """结束当前会话，清除 Redis 短期记忆。"""
    await memory.clear_all(user.id, session_id)
    return success(None, message='会话记忆已清除')
