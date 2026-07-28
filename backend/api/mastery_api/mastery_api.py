"""成员三：答案分析、掌握度、错题订正与复习 API 路由

- GET  /mastery/knowledge-points                   查询知识点掌握情况
- GET  /mastery/trend                              查询掌握度变化趋势
- GET  /mistakes                                    查询错题和订正状态
- POST /mistakes/{mistake_id}/correction            提交错题订正（须带 X-Request-ID）
- POST /mistakes/{mistake_id}/analysis              查看错题解析（VIP 或积分兑换）
- GET  /mistakes/reviews/today                      查询今日到期复习内容

user_id 一律从 JWT 获取。
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.middleware.logging import get_logger
from backend.model import get_db
from backend.model.user import User
from backend.schemas.point_event import CorrectionCompletedEvent
from backend.schemas.request.record_request import CorrectionCompletedEvent as RecordCorrectionCompletedEvent
from backend.schemas.request.mastery_request import (
    CorrectionSubmitRequest,
    KnowledgeReviewCompleteRequest,
    MistakeAnalysisRequest,
)
from backend.schemas.response.base_response import success
from backend.services.point_service.point_service import point_service
from backend.services.record_service import record_service
from backend.services.vip_service.vip_service import vip_service
from backend.services.mastery_service.mastery_service import (
    MasteryService,
    get_mastery_service,
)
from backend.services.knowledge_review_service import knowledge_review_service

mastery_router = APIRouter()
logger = get_logger(__name__)
_TZ = timezone(timedelta(hours=8))


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

@mastery_router.get('/knowledge-reviews/card')
async def get_knowledge_review_card(
        knowledge_point_name: str = Query(..., min_length=1, max_length=128),
        subject: str = Query(None, max_length=32),
        mode: str = Query('full', pattern='^(quick|full|advanced)$'),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    """获取个性化知识点复习卡、概念自测和关联错题。"""
    data = await knowledge_review_service.get_card(
        db,
        user_id=user.id,
        knowledge_point_name=knowledge_point_name,
        subject=subject,
        mode=mode,
    )
    return success(data)


@mastery_router.post('/knowledge-reviews/complete')
async def complete_knowledge_review(
        req: KnowledgeReviewCompleteRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """提交概念自测并记录一次知识点复习。"""
    data = await knowledge_review_service.complete(
        db, user_id=user.id, payload=req, request_id=x_request_id
    )
    return success(data)

@mastery_router.get('/mistakes')
async def list_mistakes(
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, description='每页数量'),
        status: str = Query(None, description='筛选状态: pending/corrected/review_due'),
        subject: str = Query(None, description='按答题时的学科快照筛选'),
        knowledge_point_name: str = Query(None, max_length=128, description='按知识点筛选关联错题'),
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询当前学生的错题列表。"""
    data = await service.get_mistakes(
        user.id, page=page, page_size=page_size, status=status, subject=subject,
        knowledge_point_name=knowledge_point_name,
    )
    return success(data.model_dump())


@mastery_router.post('/mistakes/{mistake_id}/correction')
async def submit_correction(
        mistake_id: int,
        req: CorrectionSubmitRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: MasteryService = Depends(get_mastery_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """提交错题订正：判断订正正误，首次成功生成 1/3/7 天复习计划。"""
    data = await service.submit_correction(user.id, mistake_id, req, x_request_id)
    if data.first_success:
        completed_at = datetime.now(_TZ)
        try:
            await point_service.reward_correction(
                db,
                CorrectionCompletedEvent(
                    request_id=x_request_id,
                    user_id=user.id,
                    occurred_at=completed_at,
                    mistake_id=mistake_id,
                    first_success=True,
                ),
            )
        except Exception:
            logger.exception("订正成功，但积分奖励失败 mistake_id=%s", mistake_id)
        try:
            await record_service.record_correction(
                RecordCorrectionCompletedEvent(
                    request_id=x_request_id,
                    user_id=user.id,
                    mistake_id=mistake_id,
                    subject=data.subject,
                    knowledge_point_id=data.knowledge_point_id,
                    knowledge_point_name=data.knowledge_point_name,
                    first_success=True,
                    completed_at=completed_at,
                )
            )
        except Exception:
            logger.exception("订正成功，但学习记录写入失败 mistake_id=%s", mistake_id)
    return success(data.model_dump())


@mastery_router.get('/mistakes/reviews/today')
async def get_today_reviews(
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """查询今日到期且未完成的错题复习列表。"""
    data = await service.get_today_reviews(user.id)
    return success([item.model_dump() for item in data])


@mastery_router.post('/mistakes/{mistake_id}/analysis')
async def get_mistake_analysis(
        mistake_id: int,
        req: MistakeAnalysisRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: MasteryService = Depends(get_mastery_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """查看错题解析：VIP 直接查看详细解析；普通用户可积分兑换（10 积分）或仅查看简单解析。"""
    data = await service.get_mistake_analysis(user.id, mistake_id)
    if req.payment_method == "basic":
        # 标准答案和简单解析对所有用户开放，绝不能在该分支扣除积分。
        data.detailed_analysis = None
        data.payment_method = "basic"
    else:
        auth = await vip_service.authorize_feature(
            db,
            user_id=user.id,
            feature="detailed_analysis",
            payment_method=req.payment_method,
            request_id=x_request_id,
        )
        data.payment_method = auth.get("payment_method")
    return success(data.model_dump())


@mastery_router.post('/mistakes/{mistake_id}/reviews/{review_id}/reveal')
async def reveal_review_answer(
        mistake_id: int,
        review_id: int,
        user: User = Depends(get_current_user),
        service: MasteryService = Depends(get_mastery_service),
):
    """记录本轮"不会"，展示答案与解析，保留后续 1/3/7 天复习安排。"""
    data = await service.reveal_review_answer(user.id, mistake_id, review_id)
    return success(data.model_dump())
