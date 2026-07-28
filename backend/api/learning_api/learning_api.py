"""成员二：智能诊断与练习生成 API 路由 (/learning)

- POST /learning/diagnose                          学情诊断
- POST /learning/practices                         创建练习组（须带 X-Request-ID）
- GET  /learning/practices/{practice_id}           查询练习组
- POST /learning/practices/{practice_id}/answers   提交答案（须带 X-Request-ID）

user_id 一律从 JWT 获取；练习查询不返回标准答案。
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.middleware.logging import get_logger
from backend.model import get_db
from backend.model.user import User
from backend.schemas.point_event import PracticeCompletedEvent as PointPracticeCompletedEvent
from backend.schemas.request.record_request import PracticeCompletedEvent as RecordPracticeCompletedEvent
from backend.schemas.response.mastery_response import AnswerResultEvent
from backend.services.mastery_service.mastery_service import get_mastery_service
from backend.services.point_service.point_service import point_service
from backend.services.record_service import record_service
from backend.services.vip_service.vip_service import vip_service
from backend.schemas.request.learning_request import (
    DiagnosisRequest,
    PracticeGenerateRequest,
    AnswerSubmitRequest,
    DetailedAnalysisRequest,
)
from backend.schemas.response.base_response import success
from backend.services.learning_service.learning_service import (
    LearningService,
    get_learning_service,
)
from backend.core.exceptions import BusinessError

learning_router = APIRouter(prefix='/learning', tags=['智能诊断与练习'])
logger = get_logger(__name__)
_TZ = timezone(timedelta(hours=8))


@learning_router.post('/diagnose')
async def diagnose(
        req: DiagnosisRequest,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
):
    """学情诊断：识别知识点、评估掌握度、给出薄弱点与练习建议。"""
    data = await service.diagnose(user.id, req)
    return success(data.model_dump())


@learning_router.post('/practices')
async def create_practice(
        req: PracticeGenerateRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: LearningService = Depends(get_learning_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """创建针对性练习组（内容校验 + 一次自动重试 + 幂等）。"""
    entitlement = await vip_service.check_entitlement(
        db, user_id=user.id, feature="practice_generation"
    )
    data = await service.generate_practice(user.id, x_request_id, req)
    await vip_service.consume_usage(
        db,
        user_id=user.id,
        feature="practice_generation",
        request_id=x_request_id,
        usage_source=entitlement.get("usage_source", "quota"),
    )
    return success(data.model_dump(), message='练习生成成功')


@learning_router.get('/practices/{practice_id}')
async def get_practice(
        practice_id: int,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
):
    """查询练习组（仅限本人，不含标准答案）。"""
    data = await service.get_practice(user.id, practice_id)
    return success(data.model_dump())


@learning_router.post('/practices/{practice_id}/answers')
async def submit_answers(
        practice_id: int,
        req: AnswerSubmitRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: LearningService = Depends(get_learning_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """提交练习答案：判题、错因分类、难度调整并派发业务事件。"""
    # Keep only the scalar identifier across transaction boundaries. Point
    # rewards commit/rollback the request session, which may expire ORM
    # attributes; reading user.id afterwards can otherwise trigger an implicit
    # async load outside greenlet_spawn (MissingGreenlet).
    user_id = user.id
    data = await service.submit_answers(user_id, practice_id, x_request_id, req)
    practice = await service.get_practice(user_id, practice_id)
    sync_failures = []

    try:
        mastery_service = await get_mastery_service()
        questions = {item.question_id: item for item in practice.questions}
        submitted_answers = {item.question_id: item.answer for item in req.answers}
        for result in data.results:
            question = questions.get(result.question_id)
            await mastery_service.process_answer(AnswerResultEvent(
                request_id=f"{x_request_id}:q:{result.question_id}",
                user_id=user_id,
                practice_id=practice_id,
                question_id=result.question_id,
                knowledge_point_id=question.knowledge_point_id if question else None,
                knowledge_point_name=question.knowledge_point_name if question else None,
                subject=practice.subject,
                difficulty=question.difficulty if question else (data.current_difficulty or "easy"),
                is_correct=result.is_correct,
                error_type=result.error_type,
                question_content=question.content if question else None,
                user_answer=submitted_answers.get(result.question_id),
                standard_answer=result.standard_answer,
                answered_at=datetime.now(_TZ).isoformat(),
            ))
    except Exception:
        logger.exception("练习已提交，但掌握度/错题处理失败 practice_id=%s", practice_id)
        sync_failures.append("mastery")

    completed_at = datetime.now(_TZ)
    record_event = RecordPracticeCompletedEvent(
        request_id=x_request_id,
        user_id=user_id,
        practice_id=practice_id,
        subject=practice.subject,
        knowledge_point_id=practice.knowledge_point_id,
        knowledge_point_name=practice.knowledge_point_name,
        question_count=data.question_count,
        correct_count=data.correct_count,
        accuracy=data.accuracy,
        is_valid=True,
        completed_at=completed_at,
    )
    try:
        await record_service.record_practice(record_event)
        await record_service.update_plan_progress(record_event)
    except Exception:
        logger.exception("练习已提交，但学习记录/今日计划更新失败 practice_id=%s", practice_id)
        sync_failures.append("records")
    try:
        await point_service.reward_practice(
            db,
            PointPracticeCompletedEvent(
                request_id=x_request_id,
                user_id=user_id,
                occurred_at=completed_at,
                practice_id=practice_id,
                is_valid=True,
            ),
        )
        await point_service.reward_streak_if_eligible(
            db,
            user_id=user_id,
            occurred_at=completed_at,
        )
    except Exception:
        logger.exception("练习已提交，但积分奖励失败 practice_id=%s", practice_id)
        sync_failures.append("points")
    if sync_failures:
        raise BusinessError(
            "LEARNING_SYNC_FAILED",
            f"答案已保存，但学习数据同步失败（{','.join(sync_failures)}），请使用相同请求重试",
            503,
        )
    payload = data.model_dump()
    for item in payload["results"]:
        item["error_description"] = None
        item["next_suggestion"] = None
    return success(payload, message='答案分析完成')


@learning_router.post('/practices/{practice_id}/detailed-analysis')
async def unlock_detailed_analysis(
        practice_id: int,
        req: DetailedAnalysisRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: LearningService = Depends(get_learning_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """VIP 直接使用；普通用户扣 10 积分后返回详细错因和建议。"""
    data = await service.get_detailed_analysis(user.id, practice_id)
    await vip_service.authorize_feature(
        db,
        user_id=user.id,
        feature="detailed_analysis",
        payment_method=req.payment_method,
        request_id=x_request_id,
    )
    return success({"practice_id": practice_id, "items": data})
