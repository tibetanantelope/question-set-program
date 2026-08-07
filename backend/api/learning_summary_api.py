"""成员二 用户端 API：个人学情摘要。

- GET /mastery/summary   当前用户学情摘要（总体掌握度、分布、薄弱点、待办）

只读、user_id 一律来自 JWT；契约第 3 节 `/mastery/*` 归成员二。
单独成文，避免改动成员三的 mastery_api.py。
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.learning_summary_service import learning_summary_service

learning_summary_router = APIRouter(tags=["用户-学情摘要"])


@learning_summary_router.get("/mastery/summary")
async def mastery_summary(
    weak_limit: int = Query(5, ge=1, le=20, description="薄弱知识点返回数量"),
    user: User = Depends(get_current_user),
):
    """当前登录用户的学情摘要（首页学习概览）。"""
    data = await learning_summary_service.get_summary(user.id, weak_limit=weak_limit)
    return success(data)
