"""成员二 管理员端 API：运营看板统计。

- GET /admin/dashboard/overview   运营总览卡片（用户/练习/错题/复习/掌握度分布）
- GET /admin/dashboard/subjects   学科分布（练习次数、平均正确率）
- GET /admin/dashboard/trend      近 N 天学习活跃趋势（练习次数、活跃用户）

全部只读、仅返回聚合数据；普通用户访问返回 403（get_current_admin）。
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_admin
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.admin_dashboard_service import admin_dashboard_service

admin_dashboard_router = APIRouter(prefix="/admin/dashboard", tags=["管理员-运营看板"])


@admin_dashboard_router.get("/overview")
async def dashboard_overview(
    days: int = Query(7, ge=1, le=90, description="活跃/新增用户统计窗口天数"),
    admin: User = Depends(get_current_admin),
):
    """运营首页统计卡片。"""
    data = await admin_dashboard_service.get_overview(days=days)
    return success(data)


@admin_dashboard_router.get("/subjects")
async def dashboard_subjects(
    admin: User = Depends(get_current_admin),
):
    """按学科聚合练习次数与平均正确率。"""
    data = await admin_dashboard_service.get_subject_distribution()
    return success(data)


@admin_dashboard_router.get("/trend")
async def dashboard_trend(
    days: int = Query(7, ge=1, le=90, description="趋势统计天数（近 N 天）"),
    admin: User = Depends(get_current_admin),
):
    """近 N 天学习活跃趋势，缺失日期补零。"""
    data = await admin_dashboard_service.get_trend(days=days)
    return success(data)
