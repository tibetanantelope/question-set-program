"""成员四 管理员端 API：错题、复习与学习报告管理。

- GET  /admin/learning/mistakes        用户错题统计（数量、错因、订正率）
- GET  /admin/learning/reviews          复习完成率和到期复习情况
- GET  /admin/learning/weak-points      用户薄弱知识点
- GET  /admin/learning/users/{id}/summary  单个用户学习轨迹摘要
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_admin
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.admin_learning_service import admin_learning_service

admin_learning_router = APIRouter(prefix="/admin/learning", tags=["管理员-学习管理"])


# ─── 错题统计 ─────────────────────────────────


@admin_learning_router.get("/mistakes")
async def admin_mistake_stats(
    user_id: int | None = Query(None, description="指定用户ID，不传则查全部"),
    subject: str | None = Query(None, description="学科筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
):
    """查看用户错题数量、主要错因和订正率。"""
    data = await admin_learning_service.get_mistake_stats(
        user_id=user_id,
        subject=subject,
        page=page,
        page_size=page_size,
    )
    return success(data)


# ─── 复习情况 ─────────────────────────────────


@admin_learning_router.get("/reviews")
async def admin_review_stats(
    user_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
):
    """查看复习完成率和到期复习情况。"""
    data = await admin_learning_service.get_review_stats(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return success(data)


# ─── 薄弱知识点 ─────────────────────────────────


@admin_learning_router.get("/weak-points")
async def admin_weak_points(
    user_id: int | None = Query(None),
    subject: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
):
    """查看用户薄弱知识点。"""
    data = await admin_learning_service.get_weak_points(
        user_id=user_id,
        subject=subject,
        page=page,
        page_size=page_size,
    )
    return success(data)


# ─── 用户学习轨迹摘要 ──────────────────────────


@admin_learning_router.get("/users/{user_id}/summary")
async def admin_user_learning_summary(
    user_id: int,
    admin: User = Depends(get_current_admin),
):
    """查看单个用户的学习轨迹摘要。"""
    data = await admin_learning_service.get_user_learning_summary(user_id)
    return success(data)
