"""成员三：答案分析、掌握度、错题订正与复习 Service。

职责（对齐《五人任务分工》第 6 节 + 《业务设计》第 7 节）：
- 知识点掌握度计算和状态更新；
- 答题记录和错题记录持久化；
- 错题订正流程（判断正误、1/3/7 天复习计划）；
- 掌握度趋势和高频错因统计；
- 写操作幂等（request_id）；
- 首次订正成功后触发 CorrectionCompletedEvent（成员五消费）。
"""

import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from backend.core.exceptions import BusinessError
from backend.dao.mastery_mapper import MasteryMapper
from backend.model.mastery import AnswerRecord, KnowledgeMastery, Mistake, ReviewPlan
from backend.schemas.request.mastery_request import CorrectionSubmitRequest
from backend.schemas.response.mastery_response import (
    AnswerResultEvent,
    CorrectionCompletedEvent,
    CorrectionResponse,
    MasterySummary,
    MasteryListResponse,
    TrendPoint,
    TrendResponse,
    MistakeItem,
    MistakeListResponse,
    ReviewItem,
)

# 掌握度变化规则（对齐《业务设计》7.3）
_SCORE_CHANGE = {
    'easy': 3,
    'medium': 5,
    'hard': 8,
}
_SCORE_WRONG = -3

# 复习间隔天数：首次订正成功后 1 天、3 天、7 天
_REVIEW_INTERVALS = [1, 3, 7]

# 东八区
_TZ = timezone(timedelta(hours=8))


def _score_to_status(score: int) -> str:
    """掌握度 → 学习状态映射"""
    if score <= 59:
        return 'weak'
    elif score <= 80:
        return 'consolidating'
    else:
        return 'mastered'


class MasteryService:
    """答案分析、掌握度计算、错题订正与复习"""

    def __init__(self, mapper: MasteryMapper):
        self.mapper = mapper

    # ==================================================================
    # 内部方法：由成员二通过 Service 调用
    # ==================================================================

    async def process_answer(self, event: AnswerResultEvent) -> dict:
        """处理单道题的答题结果（成员二调用）。

        1. 幂等检查
        2. 查询/创建 knowledge_mastery
        3. 计算掌握度变化 → 更新 → 确定 learning_status
        4. 写入 answer_record
        5. 答错 → 创建 mistake 记录
        6. 返回 {mastery_before, mastery_after, learning_status, mistake_id}
        """
        # 幂等检查
        existing = await self.mapper.get_answer_record_by_request_id(
            event.user_id, event.request_id
        )
        if existing:
            return self._build_process_result(existing)

        kp_id = event.knowledge_point_id or 0
        kp_name = event.knowledge_point_name or ''
        mastery_before = 60

        # 查询或创建掌握度
        mastery = await self.mapper.get_mastery(event.user_id, kp_id)
        if mastery:
            mastery_before = mastery.mastery_score
        else:
            mastery = KnowledgeMastery(
                user_id=event.user_id,
                knowledge_point_id=kp_id,
                knowledge_point_name=kp_name,
                mastery_score=60,
                learning_status='consolidating',
                answer_count=0,
                correct_count=0,
            )
            mastery = await self.mapper.create_mastery(mastery)

        # 计算掌握度变化
        if event.is_correct:
            score_change = _SCORE_CHANGE.get(event.difficulty, 3)
        else:
            score_change = _SCORE_WRONG

        new_score = max(0, min(100, mastery_before + score_change))
        new_status = _score_to_status(new_score)

        # 更新掌握度
        await self.mapper.update_mastery(mastery.id, score_change, event.is_correct, new_status)

        # 创建答题记录
        record = AnswerRecord(
            user_id=event.user_id,
            practice_id=event.practice_id,
            question_id=event.question_id,
            knowledge_point_id=kp_id if kp_id > 0 else None,
            knowledge_point_name=kp_name,
            difficulty=event.difficulty,
            user_answer='',  # answer_record 由成员二填充，此处为基础记录
            is_correct=event.is_correct,
            error_type=event.error_type,
            error_description='',
            request_id=event.request_id,
        )
        record = await self.mapper.create_answer_record(record)

        # 答错 → 创建错题
        mistake_id = None
        if not event.is_correct:
            mistake = Mistake(
                user_id=event.user_id,
                question_id=event.question_id,
                question_content='',
                user_answer='',
                standard_answer='',
                knowledge_point_id=kp_id if kp_id > 0 else None,
                knowledge_point_name=kp_name,
                difficulty=event.difficulty,
                error_type=event.error_type,
                correction_status='pending',
            )
            mistake = await self.mapper.create_mistake(mistake)
            mistake_id = mistake.id

        return {
            'mastery_before': mastery_before,
            'mastery_after': new_score,
            'learning_status': new_status,
            'mistake_id': mistake_id,
        }

    def _build_process_result(self, existing_record: AnswerRecord) -> dict:
        """根据已存在的答题记录构造幂等返回。"""
        return {
            'mastery_before': None,
            'mastery_after': None,
            'learning_status': None,
            'mistake_id': None,
            'idempotent': True,
        }

    # ==================================================================
    # 9.1 查询知识点掌握情况
    # ==================================================================

    async def get_masteries(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> MasteryListResponse:
        """分页查询知识点掌握度列表。"""
        items, total = await self.mapper.list_masteries(user_id, page, page_size, status)
        pages = math.ceil(total / page_size) if total > 0 else 0
        summaries = [
            MasterySummary(
                knowledge_point_id=m.knowledge_point_id,
                knowledge_point_name=m.knowledge_point_name,
                mastery_score=m.mastery_score,
                learning_status=m.learning_status,
                answer_count=m.answer_count or 0,
                correct_count=m.correct_count or 0,
                last_studied_at=m.last_studied_at.isoformat() if m.last_studied_at else None,
            )
            for m in items
        ]
        return MasteryListResponse(
            items=summaries,
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
        )

    # ==================================================================
    # 9.2 查询掌握度趋势
    # ==================================================================

    async def get_mastery_trend(self, user_id: int, days: int = 7) -> TrendResponse:
        """查询掌握度变化趋势。"""
        rows = await self.mapper.get_mastery_trend_days(user_id, days)
        if not rows:
            return TrendResponse(current_score=0, change=0, points=[])

        points = [TrendPoint(date=d, score=s) for d, s in rows]
        current_score = points[-1].score if points else 0
        first_score = points[0].score if points else current_score
        change = current_score - first_score

        return TrendResponse(
            current_score=current_score,
            change=change,
            points=points,
        )

    # ==================================================================
    # 9.3 查询错题
    # ==================================================================

    async def get_mistakes(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> MistakeListResponse:
        """分页查询错题列表。"""
        items, total = await self.mapper.list_mistakes(user_id, page, page_size, status)
        pages = math.ceil(total / page_size) if total > 0 else 0
        summaries = [
            MistakeItem(
                mistake_id=m.id,
                question_id=m.question_id,
                question_content=m.question_content,
                user_answer=m.user_answer,
                standard_answer=m.standard_answer,
                knowledge_point_id=m.knowledge_point_id,
                knowledge_point_name=m.knowledge_point_name,
                error_type=m.error_type,
                correction_status=m.correction_status,
                next_review_at=m.next_review_at.isoformat() if m.next_review_at else None,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in items
        ]
        return MistakeListResponse(
            items=summaries,
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
        )

    # ==================================================================
    # 9.4 提交错题订正
    # ==================================================================

    async def submit_correction(
        self,
        user_id: int,
        mistake_id: int,
        req: CorrectionSubmitRequest,
        request_id: str,
    ) -> CorrectionResponse:
        """提交错题订正。

        1. 幂等检查
        2. 验证错题归属
        3. 比对订正答案（简易判断：与 standard_answer 完全匹配）
        4. 首次成功 → 生成 1/3/7 天 review_plan → 发送 CorrectionCompletedEvent
        5. 返回订正结果
        """
        # 幂等检查
        existing = await self.mapper.get_mistake_by_correction_request(user_id, request_id)
        if existing:
            return CorrectionResponse(
                mistake_id=existing.id,
                is_correct=existing.correction_correct,
                correction_status=existing.correction_status,
                first_success=existing.first_correction_success,
                review_dates=[],
            )

        # 验证错题归属
        mistake = await self.mapper.get_mistake(mistake_id, user_id)
        if not mistake:
            raise BusinessError('MISTAKE_NOT_FOUND', '错题不存在', 404)

        # 判断订正答案
        standard = (mistake.standard_answer or '').strip().lower()
        answer = req.answer.strip().lower()
        is_correct = (answer == standard)

        # 首次订正成功判定
        first_success = is_correct and not mistake.first_correction_success

        # 更新错题订正结果
        mistake = await self.mapper.update_mistake_correction(
            mistake_id=mistake_id,
            answer=req.answer,
            is_correct=is_correct,
            first_success=first_success,
            request_id=request_id,
        )

        # 首次成功 → 生成复习计划
        review_dates: List[str] = []
        if first_success:
            today = date.today()
            plans = []
            for interval in _REVIEW_INTERVALS:
                review_date = today + timedelta(days=interval)
                plans.append(ReviewPlan(
                    user_id=user_id,
                    mistake_id=mistake_id,
                    knowledge_point_id=mistake.knowledge_point_id,
                    knowledge_point_name=mistake.knowledge_point_name,
                    review_date=review_date,
                    status='pending',
                ))
                review_dates.append(review_date.isoformat())
            await self.mapper.create_review_plans(plans)
            # 设置最近一次复习时间
            next_review = today + timedelta(days=_REVIEW_INTERVALS[0])
            await self.mapper.set_mistake_next_review(
                mistake_id, datetime.combine(next_review, datetime.min.time(), tzinfo=_TZ)
            )

            # TODO: 发送 CorrectionCompletedEvent 给成员五
            # event = CorrectionCompletedEvent(
            #     request_id=request_id,
            #     user_id=user_id,
            #     mistake_id=mistake_id,
            #     knowledge_point_id=mistake.knowledge_point_id,
            #     first_success=True,
            #     completed_at=datetime.now(_TZ).isoformat(),
            # )
            # await point_service.on_correction_completed(event)

        return CorrectionResponse(
            mistake_id=mistake_id,
            is_correct=is_correct,
            correction_status=mistake.correction_status,
            first_success=first_success,
            review_dates=review_dates,
        )

    # ==================================================================
    # 9.5 查询今日复习
    # ==================================================================

    async def get_today_reviews(self, user_id: int) -> List[ReviewItem]:
        """查询今日到期且未完成的错题复习列表。"""
        rows = await self.mapper.get_today_reviews(user_id)
        return [
            ReviewItem(
                review_id=plan.id,
                mistake_id=mistake.id,
                knowledge_point_id=mistake.knowledge_point_id,
                knowledge_point_name=mistake.knowledge_point_name,
                question_content=mistake.question_content,
                standard_answer=mistake.standard_answer,
                user_answer=mistake.user_answer,
                error_type=mistake.error_type,
                review_date=plan.review_date.isoformat(),
                status=plan.status,
            )
            for plan, mistake in rows
        ]


# 单例
_mastery_service: Optional[MasteryService] = None


async def get_mastery_service() -> MasteryService:
    global _mastery_service
    if _mastery_service is None:
        from backend.dao.mastery_mapper import get_mastery_mapper
        mapper = await get_mastery_mapper()
        _mastery_service = MasteryService(mapper)
    return _mastery_service
