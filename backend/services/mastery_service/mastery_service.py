"""成员三：答案分析、掌握度、错题订正与复习 Service。

职责（对齐《五人任务分工》第 6 节 + 《业务设计》第 7 节）：
- 知识点掌握度计算和状态更新；
- 答题记录和错题记录持久化；
- 错题订正流程（判断正误、1/3/7 天复习计划）；
- 掌握度趋势和高频错因统计；
- 写操作幂等（request_id）；
- 首次订正成功后触发 CorrectionCompletedEvent（成员五消费）。
"""

import logging
import math
import re
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
    ReviewRevealResponse,
    MistakeAnalysisResponse,
)
from backend.services.learning_service.answer_judge import judge_answers_via_llm

logger = logging.getLogger(__name__)

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


def calculate_mastery_after_answer(
    current_score: int,
    previous_answer_count: int,
    is_correct: bool,
    difficulty: str,
) -> int:
    """Evidence-based mastery update.

    A new knowledge point starts from a neutral internal prior of 50, not a
    displayed claim of 60% mastery. The expected correct rate varies by
    difficulty; early answers move the estimate strongly, while later answers
    make smaller adjustments as evidence accumulates.
    """
    expected = {"easy": 0.70, "medium": 0.50, "hard": 0.30}.get(difficulty, 0.50)
    baseline = 50 if previous_answer_count <= 0 else current_score
    learning_rate = max(10, round(40 / math.sqrt(previous_answer_count + 1)))
    outcome = 1.0 if is_correct else 0.0
    return max(0, min(100, round(baseline + learning_rate * (outcome - expected))))


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
        mastery_before = 50

        # 查询或创建掌握度
        mastery = await self.mapper.get_mastery(event.user_id, kp_id)
        if mastery:
            mastery_before = mastery.mastery_score
        else:
            mastery = KnowledgeMastery(
                user_id=event.user_id,
                knowledge_point_id=kp_id,
                knowledge_point_name=kp_name,
                mastery_score=50,
                learning_status='weak',
                answer_count=0,
                correct_count=0,
            )
            mastery = await self.mapper.create_mastery(mastery)

        # 基于题目难度、答题结果和已有证据量动态更新，不再“默认60后固定±3”。
        new_score = calculate_mastery_after_answer(
            mastery_before,
            mastery.answer_count or 0,
            event.is_correct,
            event.difficulty,
        )
        score_change = new_score - mastery_before
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
            user_answer=event.user_answer or '',
            is_correct=event.is_correct,
            error_type=event.error_type,
            error_description='',
            subject=event.subject,
            request_id=event.request_id,
        )
        record = await self.mapper.create_answer_record(record)

        # 答错 → 创建错题
        mistake_id = None
        if not event.is_correct:
            mistake = Mistake(
                user_id=event.user_id,
                question_id=event.question_id,
                question_content=event.question_content or '',
                user_answer=event.user_answer or '',
                standard_answer=event.standard_answer or '',
                knowledge_point_id=kp_id if kp_id > 0 else None,
                knowledge_point_name=kp_name,
                subject=event.subject,
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
        subject_source = items
        if status:
            subject_source, _ = await self.mapper.list_masteries(
                user_id, 1, 100, None
            )
        subject_map = (
            await self.mapper.get_mastery_subjects(
                user_id, [item.knowledge_point_name for item in subject_source]
            )
            if hasattr(self.mapper, "get_mastery_subjects")
            else {}
        )
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
                subject=subject_map.get(m.knowledge_point_name),
                evaluation_confidence=(
                    'low' if (m.answer_count or 0) < 3
                    else 'medium' if (m.answer_count or 0) < 8
                    else 'high'
                ),
                evidence_text=(
                    f'基于 {m.answer_count or 0} 道题，答对 {m.correct_count or 0} 道；'
                    + (
                        '当前证据较少，分数可能随后续答题明显变化'
                        if (m.answer_count or 0) < 3
                        else '已有一定答题证据，仍会结合后续难度与表现更新'
                        if (m.answer_count or 0) < 8
                        else '答题证据较充分，评估相对稳定'
                    )
                ),
            )
            for m in items
        ]
        return MasteryListResponse(
            items=summaries,
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
            subjects=sorted(set(subject_map.values())),
            has_unclassified=any(
                item.knowledge_point_name not in subject_map for item in subject_source
            ),
        )

    # ==================================================================
    # 9.2 查询掌握度趋势
    # ==================================================================

    async def get_mastery_trend(self, user_id: int, days: int = 7) -> TrendResponse:
        """查询掌握度变化趋势。"""
        rows = await self.mapper.get_mastery_trend_days(user_id, days)
        if not rows:
            return TrendResponse(current_score=0, change=0, points=[])

        # MySQL DATE() is returned as datetime.date by asyncmy, while the API
        # response contract exposes the date as an ISO-8601 string.
        points = [
            TrendPoint(
                date=d.isoformat() if isinstance(d, (date, datetime)) else str(d),
                score=s,
            )
            for d, s in rows
        ]
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
        subject: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
    ) -> MistakeListResponse:
        """分页查询错题列表。"""
        items, total = await self.mapper.list_mistakes(
            user_id, page, page_size, status, subject, knowledge_point_name
        )
        subjects = await self.mapper.list_mistake_subjects(user_id)
        has_unclassified = await self.mapper.has_unclassified_mistakes(user_id)
        reviewed_ids = await self.mapper.get_reviewed_mistake_ids(
            user_id, [item.id for item in items]
        )
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
                subject=m.subject,
                error_type=m.error_type,
                correction_status=m.correction_status,
                review_completed=m.id in reviewed_ids,
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
            subjects=subjects,
            has_unclassified=has_unclassified,
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
        3. 客观等价答案由本地规则快速判断，其余答案由 AI 按语义和评分约束判断
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
                subject=existing.subject,
                knowledge_point_id=existing.knowledge_point_id,
                knowledge_point_name=existing.knowledge_point_name,
            )

        # 验证错题归属
        mistake = await self.mapper.get_mistake(mistake_id, user_id)
        if not mistake:
            raise BusinessError('MISTAKE_NOT_FOUND', '错题不存在', 404)
        # Scheduled 1/3/7-day reviews are a later stage. Only the first correction
        # requires a knowledge review completed after this mistake was created.
        if (
            not req.review_id
            and mistake.correction_status != 'corrected'
            and not await self.mapper.has_completed_review_for_mistake(user_id, mistake)
        ):
            raise BusinessError(
                'KNOWLEDGE_REVIEW_REQUIRED',
                f'请先完成「{mistake.knowledge_point_name or "该知识点"}」的知识点复习，再提交订正',
                409,
            )

        # 判断订正答案
        standard = (mistake.standard_answer or '').strip()
        answer = req.answer.strip()
        is_correct = answer.casefold() == standard.casefold()
        grading_method = 'exact' if is_correct else 'fallback'
        grading_reason = '答案与参考答案一致' if is_correct else None
        if not is_correct and answer and standard:
            question_text = mistake.question_content or ''
            is_objective = bool(re.search(
                r'(选择|判断|选出|填入选项|仅填(?:数字|字母)|答案为[ABCDF]|[A-D][、.．])',
                question_text,
                re.IGNORECASE,
            ))
            judge_item = {
                'question_id': mistake.id,
                'question': question_text[:2000],
                'answer_type': 'objective' if is_objective else 'open_response',
                'standard_answer': standard[:1000],
                'analysis': '',
                'grading_spec': {
                    'subject': mistake.subject,
                    'knowledge_point': mistake.knowledge_point_name,
                    'objective_answer_strict': is_objective,
                    'open_answer_semantic_equivalence': not is_objective,
                },
                'user_answer': answer[:4000],
            }
            try:
                ai_results = await judge_answers_via_llm([judge_item])
                ai_grade = ai_results.get(mistake.id)
                if (
                    not ai_grade
                    or ai_grade['verdict'] == 'uncertain'
                    or ai_grade['confidence'] < 0.82
                ):
                    reviewed = await judge_answers_via_llm([judge_item], review=True)
                    review_grade = reviewed.get(mistake.id)
                    if review_grade and (
                        not ai_grade
                        or review_grade['verdict'] == ai_grade['verdict']
                        or review_grade['confidence'] > ai_grade['confidence']
                    ):
                        ai_grade = review_grade
                if ai_grade and ai_grade['confidence'] >= 0.75:
                    is_correct = ai_grade['verdict'] == 'correct'
                    grading_method = 'ai'
                    grading_reason = ai_grade['reason'] or (
                        '答案满足题目核心要求' if is_correct else '答案未满足题目核心要求'
                    )
            except Exception:
                logger.exception(
                    'AI correction grading failed; using exact fallback mistake_id=%s',
                    mistake.id,
                )
        if grading_reason is None:
            grading_reason = '未识别为与参考答案等价的表达，请检查题目要求和关键条件'
        if is_correct and req.review_id is not None:
            valid_review = await self.mapper.has_pending_review(req.review_id, user_id, mistake_id)
            if not valid_review:
                raise BusinessError('REVIEW_NOT_FOUND', '复习计划不存在、已完成或不属于当前用户', 404)

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

        if is_correct and req.review_id is not None:
            completed = await self.mapper.complete_review(req.review_id, user_id, mistake_id)
            if not completed:
                raise BusinessError('REVIEW_ALREADY_COMPLETED', '复习计划已完成，请刷新列表', 409)
            await self._adjust_review_mastery(user_id, mistake, 2, True)

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

            # 积分与学习记录由 API 编排层在事务成功后同步，避免 Service 循环依赖。

        return CorrectionResponse(
            mistake_id=mistake_id,
            is_correct=is_correct,
            correction_status=mistake.correction_status,
            first_success=first_success,
            review_dates=review_dates,
            subject=mistake.subject,
            knowledge_point_id=mistake.knowledge_point_id,
            knowledge_point_name=mistake.knowledge_point_name,
            grading_method=grading_method,
            grading_reason=grading_reason,
        )

    async def reveal_review_answer(
        self, user_id: int, mistake_id: int, review_id: int
    ) -> ReviewRevealResponse:
        """Record “I don't know” as this round's result and reveal learning help.

        The standard 1/3/7-day schedule remains fixed. Revealing finishes only
        the current round, applies a small mastery penalty, and leaves later
        pending rounds untouched.
        """
        revealed = await self.mapper.reveal_review(review_id, user_id, mistake_id)
        if not revealed:
            raise BusinessError(
                'REVIEW_NOT_FOUND',
                '复习计划不存在、未到期、已完成或不属于当前用户',
                404,
            )
        _plan, mistake, analysis = revealed
        mastery_after = await self._adjust_review_mastery(
            user_id, mistake, -2, False
        )
        current_round, total_rounds, next_date = await self.mapper.get_review_progress(
            user_id, mistake_id, review_id
        )
        return ReviewRevealResponse(
            review_id=review_id,
            mistake_id=mistake_id,
            standard_answer=mistake.standard_answer,
            analysis=analysis or '请对照标准答案重新梳理解题步骤，并在下一轮尝试独立作答。',
            mastery_change=-2,
            mastery_after=mastery_after,
            current_round=current_round,
            total_rounds=total_rounds or len(_REVIEW_INTERVALS),
            next_review_date=next_date.isoformat() if next_date else None,
        )

    async def _adjust_review_mastery(
        self, user_id: int, mistake: Mistake, score_change: int, is_correct: bool
    ) -> Optional[int]:
        """Apply a smaller score change than a fresh exercise attempt."""
        if not mistake.knowledge_point_id:
            return None
        mastery = await self.mapper.get_mastery(
            user_id, mistake.knowledge_point_id
        )
        if not mastery:
            return None
        new_score = max(0, min(100, mastery.mastery_score + score_change))
        await self.mapper.update_mastery(
            mastery.id,
            score_change,
            is_correct,
            _score_to_status(new_score),
        )
        return new_score

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
                subject=mistake.subject,
                question_content=mistake.question_content,
                standard_answer=mistake.standard_answer,
                user_answer=mistake.user_answer,
                error_type=mistake.error_type,
                review_date=plan.review_date.isoformat(),
                status=plan.status,
            )
            for plan, mistake in rows
        ]

    async def get_mistake_analysis(
        self, user_id: int, mistake_id: int
    ) -> MistakeAnalysisResponse:
        """获取错题解析内容（不含权限校验，由 API 层处理）。"""
        mistake = await self.mapper.get_mistake(mistake_id, user_id)
        if not mistake:
            raise BusinessError('MISTAKE_NOT_FOUND', '错题不存在', 404)

        # 尝试从关联题目获取更详细的解析
        analysis = mistake.question_content or ''
        simple_analysis = '请对照标准答案，理解本题涉及的知识点，尝试独立梳理解题思路。'
        detailed_analysis = None

        if mistake.question_id:
            question = await self.mapper.get_question(mistake.question_id)
            if question:
                if question.analysis:
                    simple_analysis = question.analysis
                if question.error_description:
                    detailed_analysis = question.error_description
                if question.next_suggestion:
                    detailed_analysis = (detailed_analysis or '') + '\n下一步建议：' + question.next_suggestion

        # 如果没有详细解析，生成一个基于错因类型的默认解析
        if not detailed_analysis and mistake.error_type:
            error_type_desc = {
                'knowledge': '知识点掌握不牢固，建议回顾相关概念和公式，做同类题巩固。',
                'calculation': '计算过程出现错误，建议分步验算，注意符号和运算顺序。',
                'reading': '审题不仔细，建议圈画关键词，明确题目条件和所求。',
                'method': '解题方法选择不当，建议总结同类题型的通用解法。',
            }
            detailed_analysis = error_type_desc.get(mistake.error_type, '建议结合标准答案，深入分析错因并总结。')

        return MistakeAnalysisResponse(
            mistake_id=mistake_id,
            standard_answer=mistake.standard_answer,
            simple_analysis=simple_analysis,
            detailed_analysis=detailed_analysis,
            error_type=mistake.error_type,
            error_description=None,
            knowledge_point_name=mistake.knowledge_point_name,
        )


# 单例
_mastery_service: Optional[MasteryService] = None


async def get_mastery_service() -> MasteryService:
    global _mastery_service
    if _mastery_service is None:
        from backend.dao.mastery_mapper import get_mastery_mapper
        mapper = await get_mastery_mapper()
        _mastery_service = MasteryService(mapper)
    return _mastery_service
