"""管理员 API：用户管理 + 操作审计。"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.dependencies import get_current_admin, get_client_ip
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.admin_service.admin_service import admin_service

admin_user_router = APIRouter(prefix='/admin/users', tags=['管理员-用户管理'])


@admin_user_router.get('')
async def list_users(
    keyword: str | None = Query(None, description='搜索：用户名或ID'),
    role: str | None = Query(None, description='角色筛选: user/admin'),
    status: str | None = Query(None, description='状态筛选: active/disabled'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
):
    """用户列表，支持搜索、筛选和分页。"""
    data = await admin_service.list_users(
        keyword=keyword, role=role, status=status, page=page, page_size=page_size,
    )
    return success(data)


@admin_user_router.get('/{user_id}')
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
):
    """查看单个用户详情（含画像信息）。"""
    data = await admin_service.get_user_detail(user_id)
    return success(data)


@admin_user_router.post('/{user_id}/disable')
async def disable_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
):
    """禁用指定用户。"""
    data = await admin_service.disable_user(user_id, admin, ip)
    return success(data, message=f'用户 {data["username"]} 已被禁用')


@admin_user_router.post('/{user_id}/restore')
async def restore_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
):
    """恢复已禁用的用户。"""
    data = await admin_service.restore_user(user_id, admin, ip)
    return success(data, message=f'用户 {data["username"]} 已恢复')
