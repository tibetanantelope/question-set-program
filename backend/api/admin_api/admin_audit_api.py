"""管理员 API：操作审计日志。"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_admin
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.admin_service.admin_service import admin_service

admin_audit_router = APIRouter(prefix='/admin/audits', tags=['管理员-审计日志'])


@admin_audit_router.get('')
async def list_audits(
    admin_id: int | None = Query(None),
    action: str | None = Query(None, description='操作类型: login/disable_user/restore_user/...'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
):
    """管理员操作审计日志列表。"""
    data = await admin_service.list_audits(
        admin_id=admin_id, action=action, page=page, page_size=page_size,
    )
    return success(data)
