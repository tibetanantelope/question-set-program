"""成员四 API：学习记录、首页推荐、每日计划、站内提醒"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.record_service import record_service

records_router = APIRouter(tags=["records"])


# ─── 历史学习记录 ─────────────────────────────────


@records_router.get("/records")
async def get_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    type: Optional[str] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
):
    items, total, pages = await record_service.get_records(
        user_id=user.id,
        page=page,
        page_size=page_size,
        record_type=type,
        subject=subject,
        date_from=date_from,
        date_to=date_to,
    )
    return success({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    })


@records_router.get("/records/stats")
async def get_records_stats(user: User = Depends(get_current_user)):
    """获取学习记录统计摘要"""
    data = await record_service.get_stats_summary(user_id=user.id)
    return success(data)


# ─── 首页推荐 ──────────────────────────────────────


@records_router.get("/recommendations/home")
async def get_home_recommendations(user: User = Depends(get_current_user)):
    data = await record_service.get_home_recommendations(user_id=user.id)
    return success(data)


# ─── 今日计划 ──────────────────────────────────────


@records_router.get("/plans/today")
async def get_today_plan(user: User = Depends(get_current_user)):
    data = await record_service.get_today_plan(user_id=user.id)
    return success(data)


# ─── 站内提醒 ──────────────────────────────────────


@records_router.get("/notifications")
async def get_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    items, total, pages = await record_service.get_notifications(
        user_id=user.id, page=page, page_size=page_size
    )
    return success({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    })


@records_router.get("/notifications/unread-count")
async def get_unread_count(user: User = Depends(get_current_user)):
    """获取未读通知数量"""
    count = await record_service.get_unread_count(user_id=user.id)
    return success({"count": count})


@records_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
):
    await record_service.mark_notification_read(user.id, notification_id)
    return success(message="已标记为已读")


@records_router.post("/notifications/read-all")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    """批量标记所有通知已读"""
    count = await record_service.mark_all_notifications_read(user.id)
    return success({"updated": count}, message=f"已将 {count} 条通知标记为已读")
