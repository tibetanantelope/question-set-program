"""成员一：用户画像与首次诊断 API 路由 (/profile)"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.request.user_profile_update_request import UserProfileUpdateRequest
from backend.schemas.request.diagnostic_request import DiagnosticSubmitRequest
from backend.schemas.response.base_response import success
from backend.services.profile_service.profile_service import ProfileService, get_profile_service
from backend.services.diagnostic_service.diagnostic_service import DiagnosticService, get_diagnostic_service

profile_router = APIRouter(prefix='/profile', tags=['用户画像'])


# ──────────────── 画像 ────────────────

@profile_router.get('/me')
async def get_my_profile(
        user: User = Depends(get_current_user),
        service: ProfileService = Depends(get_profile_service),
):
    """查询当前学生的画像和学习计划。"""
    data = await service.get_profile(user.id)
    return success(data.model_dump())


@profile_router.put('/me')
async def save_my_profile(
        req: UserProfileUpdateRequest,
        user: User = Depends(get_current_user),
        service: ProfileService = Depends(get_profile_service),
):
    """创建或更新当前学生的画像。"""
    summary = await service.save_profile(user.id, req)
    return success(summary.model_dump(), message='画像保存成功')


# ──────────────── 掌握度 ────────────────

@profile_router.get('/masteries')
async def get_my_masteries(
        user: User = Depends(get_current_user),
        service: DiagnosticService = Depends(get_diagnostic_service),
):
    """查询当前学生最近一次诊断的知识点掌握度。"""
    data = await service.get_latest_masteries(user.id)
    return success(data)


# ──────────────── 首次诊断 ────────────────

@profile_router.get('/diagnostic/status')
async def get_diagnostic_status(
        user: User = Depends(get_current_user),
        service: DiagnosticService = Depends(get_diagnostic_service),
):
    """查询是否需要首次诊断。"""
    data = await service.get_status(user.id)
    return success(data.model_dump())


@profile_router.post('/diagnostic/start')
async def start_diagnostic(
        user: User = Depends(get_current_user),
        service: DiagnosticService = Depends(get_diagnostic_service),
):
    """生成首次诊断题（5 道）。"""
    data = await service.start_diagnostic(user.id)
    return success(data.model_dump())


@profile_router.post('/diagnostic/submit')
async def submit_diagnostic(
        req: DiagnosticSubmitRequest,
        user: User = Depends(get_current_user),
        service: DiagnosticService = Depends(get_diagnostic_service),
):
    """提交首次诊断答案并初始化掌握度。"""
    data = await service.submit_diagnostic(user.id, req)
    return success(data.model_dump())


@profile_router.post('/diagnostic/skip')
async def skip_diagnostic(
        user: User = Depends(get_current_user),
        service: DiagnosticService = Depends(get_diagnostic_service),
):
    """跳过诊断，使用默认掌握度 60。"""
    data = await service.skip_diagnostic(user.id)
    return success(data.model_dump(), message='已跳过首次诊断，使用默认掌握度')
