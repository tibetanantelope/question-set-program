"""成员三：答案分析、掌握度、错题订正与复习 API 路由

- GET  /mastery/knowledge-points                   查询知识点掌握情况
- GET  /mastery/trend                              查询掌握度变化趋势
- GET  /mistakes                                    查询错题和订正状态
- POST /mistakes/{mistake_id}/correction            提交错题订正（须带 X-Request-ID）
- GET  /mistakes/reviews/today                      查询今日到期复习内容

user_id 一律从 JWT 获取。
"""

from fastapi import APIRouter, Depends, Header, Query

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.request.mastery_request import CorrectionSubmitRequest
from backend.schemas.response.base_response import success
from backend.services.mastery_service.mastery_service import (
    MasteryService,
    get_mastery_service,
)

mastery_router = APIRouter()


# ==================== 知识点掌握度 ====================

@mastery_router.get('/mastery/knowledge-points')
async def list_masteries(
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, description='每页数量'),
        status: str = Query(None, description='筛选学习状态: weak/consolidating/mastered'),
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询当前学生的知识点掌握情况。"""
    data = await service.get_masteries(user.id, page=page, page_size=page_size, status=status)
    return success(data.model_dump())


@mastery_router.get('/mastery/trend')
async def get_mastery_trend(
        days: int = Query(7, ge=1, le=90, description='统计天数'),
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询当前学生的掌握度变化趋势。"""
    data = await service.get_mastery_trend(user.id, days=days)
    return success(data.model_dump())


# ==================== 错题 ====================

@mastery_router.get('/mistakes')
async def list_mistakes(
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, description='每页数量'),
        status: str = Query(None, description='筛选状态: pending/corrected/review_due'),
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询当前学生的错题列表。"""
    data = await service.get_mistakes(user.id, page=page, page_size=page_size, status=status)
    return success(data.model_dump())


@mastery_router.post('/mistakes/{mistake_id}/correction')
async def submit_correction(
        mistake_id: int,
        req: CorrectionSubmitRequest,
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """提交错题订正：判断订正正误，首次成功生成 1/3/7 天复习计划。"""
    data = await service.submit_correction(user.id, mistake_id, req, x_request_id)
    return success(data.model_dump())


@mastery_router.get('/mistakes/reviews/today')
async def get_today_reviews(
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询今日到期且未完成的错题复习列表。"""
    data = await service.get_today_reviews(user.id)
    return success([item.model_dump() for item in data])
