"""成员三：答题记录、掌握度、错题和复习计划的数据访问层"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, case, exists
from sqlalchemy.exc import SQLAlchemyError

from backend.model import AsyncSessionLocal
from backend.model.mastery import (
    AnswerRecord,
    KnowledgeMastery,
    KnowledgeReviewRecord,
    Mistake,
    ReviewPlan,
)
from backend.model.learning import Question
from backend.model.learning_models import LearningRecord

# 东八区
_TZ = timezone(timedelta(hours=8))


class MasteryMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_reviewed_mistake_ids(
        self, user_id: int, mistake_ids: list[int]
    ) -> set[int]:
        """Return mistakes whose exact knowledge point was reviewed after the mistake."""
        if not mistake_ids:
            return set()
        async with self.session_factory() as session:
            stmt = (
                select(Mistake.id)
                .join(
                    KnowledgeReviewRecord,
                    and_(
                        KnowledgeReviewRecord.user_id == Mistake.user_id,
                        KnowledgeReviewRecord.knowledge_point_name
                        == Mistake.knowledge_point_name,
                        KnowledgeReviewRecord.completed_at >= Mistake.created_at,
                        (
                            (Mistake.subject.is_(None))
                            | (KnowledgeReviewRecord.subject.is_(None))
                            | (KnowledgeReviewRecord.subject == Mistake.subject)
                        ),
                    ),
                )
                .where(
                    Mistake.user_id == user_id,
                    Mistake.id.in_(mistake_ids),
                )
                .distinct()
            )
            return set((await session.execute(stmt)).scalars().all())

    async def has_completed_review_for_mistake(
        self, user_id: int, mistake: Mistake
    ) -> bool:
        reviewed = await self.get_reviewed_mistake_ids(user_id, [mistake.id])
        return mistake.id in reviewed

    # ========== 答题记录 ==========

    async def get_answer_record_by_request_id(self, user_id: int, request_id: str) -> Optional[AnswerRecord]:
        """幂等查询：根据 request_id 返回已存在的答题记录。"""
        async with self.session_factory() as session:
            stmt = select(AnswerRecord).where(
                AnswerRecord.user_id == user_id,
                AnswerRecord.request_id == request_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_answer_record(self, record: AnswerRecord) -> AnswerRecord:
        """创建答题记录。"""
        async with self.session_factory() as session:
            try:
                session.add(record)
                await session.commit()
                await session.refresh(record)
                return record
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ========== 知识点掌握度 ==========

    async def get_mastery(self, user_id: int, knowledge_point_id: int) -> Optional[KnowledgeMastery]:
        """查询用户在指定知识点的掌握度。"""
        async with self.session_factory() as session:
            stmt = select(KnowledgeMastery).where(
                KnowledgeMastery.user_id == user_id,
                KnowledgeMastery.knowledge_point_id == knowledge_point_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_mastery_by_name(
        self, user_id: int, knowledge_point_name: str
    ) -> Optional[KnowledgeMastery]:
        """按具体知识点名称读取最近的真实掌握度记录。"""
        async with self.session_factory() as session:
            stmt = (
                select(KnowledgeMastery)
                .where(
                    KnowledgeMastery.user_id == user_id,
                    KnowledgeMastery.knowledge_point_name == knowledge_point_name,
                )
                .order_by(KnowledgeMastery.updated_at.desc(), KnowledgeMastery.id.desc())
                .limit(1)
            )
            return (await session.execute(stmt)).scalar_one_or_none()

    async def create_mastery(self, mastery: KnowledgeMastery) -> KnowledgeMastery:
        """创建知识点掌握度记录。"""
        async with self.session_factory() as session:
            try:
                session.add(mastery)
                await session.commit()
                await session.refresh(mastery)
                return mastery
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def update_mastery(
        self,
        mastery_id: int,
        score_change: int,
        is_correct: bool,
        new_status: str,
    ) -> KnowledgeMastery:
        """更新掌握度：增减分数、更新答题计数和状态，在同一事务中完成。"""
        async with self.session_factory() as session:
            try:
                stmt = select(KnowledgeMastery).where(KnowledgeMastery.id == mastery_id)
                r = await session.execute(stmt)
                m = r.scalar_one_or_none()
                if not m:
                    raise ValueError(f"KnowledgeMastery id={mastery_id} not found")
                m.mastery_score = max(0, min(100, m.mastery_score + score_change))
                m.learning_status = new_status
                m.answer_count = (m.answer_count or 0) + 1
                if is_correct:
                    m.correct_count = (m.correct_count or 0) + 1
                m.last_studied_at = datetime.now(_TZ)
                await session.commit()
                await session.refresh(m)
                return m
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def list_masteries(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[KnowledgeMastery], int]:
        """分页查询知识点掌握度列表。"""
        async with self.session_factory() as session:
            base = select(KnowledgeMastery).where(KnowledgeMastery.user_id == user_id)
            if status:
                base = base.where(KnowledgeMastery.learning_status == status)
            # 总数
            count_stmt = select(func.count()).select_from(base.subquery())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0
            # 分页
            stmt = (
                base
                .order_by(KnowledgeMastery.mastery_score.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())
            return items, total

    async def get_mastery_trend_days(
        self,
        user_id: int,
        days: int = 7,
    ) -> List[Tuple[str, int]]:
        """获取最近 N 天的掌握度趋势（按知识点聚合后的日均掌握度）。"""
        async with self.session_factory() as session:
            since = datetime.now(_TZ) - timedelta(days=days)
            # 查询每天有更新的知识点的最后掌握度，按天聚合 AVG
            stmt = (
                select(
                    func.date(KnowledgeMastery.updated_at).label('d'),
                    func.avg(KnowledgeMastery.mastery_score).label('avg_score'),
                )
                .where(
                    KnowledgeMastery.user_id == user_id,
                    KnowledgeMastery.updated_at >= since,
                )
                .group_by(func.date(KnowledgeMastery.updated_at))
                .order_by('d')
            )
            result = await session.execute(stmt)
            return [(row.d, int(row.avg_score)) for row in result.all()]

    async def get_mastery_subjects(
        self, user_id: int, knowledge_point_names: List[str]
    ) -> dict[str, str]:
        """按最近答题或错题快照推断知识点所属学科/大学课程。"""
        if not knowledge_point_names:
            return {}
        async with self.session_factory() as session:
            mapping: dict[str, str] = {}
            rows = (
                await session.execute(
                    select(
                        AnswerRecord.knowledge_point_name,
                        AnswerRecord.subject,
                        AnswerRecord.created_at,
                    )
                    .where(
                        AnswerRecord.user_id == user_id,
                        AnswerRecord.knowledge_point_name.in_(knowledge_point_names),
                        AnswerRecord.subject.is_not(None),
                        AnswerRecord.subject != '',
                    )
                    .order_by(AnswerRecord.created_at.desc())
                )
            ).all()
            for name, subject, _ in rows:
                if name and subject and name not in mapping:
                    mapping[name] = subject

            missing = [name for name in knowledge_point_names if name not in mapping]
            if missing:
                rows = (
                    await session.execute(
                        select(Mistake.knowledge_point_name, Mistake.subject, Mistake.created_at)
                        .where(
                            Mistake.user_id == user_id,
                            Mistake.knowledge_point_name.in_(missing),
                            Mistake.subject.is_not(None),
                            Mistake.subject != '',
                        )
                        .order_by(Mistake.created_at.desc())
                    )
                ).all()
                for name, subject, _ in rows:
                    if name and subject and name not in mapping:
                        mapping[name] = subject
            missing = [name for name in knowledge_point_names if name not in mapping]
            if missing:
                rows = (
                    await session.execute(
                        select(
                            LearningRecord.knowledge_point_name,
                            LearningRecord.subject,
                            LearningRecord.occurred_at,
                        )
                        .where(
                            LearningRecord.user_id == user_id,
                            LearningRecord.knowledge_point_name.in_(missing),
                            LearningRecord.subject.is_not(None),
                            LearningRecord.subject != '',
                        )
                        .order_by(LearningRecord.occurred_at.desc())
                    )
                ).all()
                for name, subject, _ in rows:
                    if name and subject and name not in mapping:
                        mapping[name] = subject
            return mapping

    # ========== 错题 ==========

    async def create_mistake(self, mistake: Mistake) -> Mistake:
        """创建错题记录。"""
        async with self.session_factory() as session:
            try:
                session.add(mistake)
                await session.commit()
                await session.refresh(mistake)
                return mistake
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_mistake(self, mistake_id: int, user_id: int) -> Optional[Mistake]:
        """查询单条错题（仅限本人）。"""
        async with self.session_factory() as session:
            stmt = select(Mistake).where(
                Mistake.id == mistake_id,
                Mistake.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_mistake_by_correction_request(
        self, user_id: int, request_id: str
    ) -> Optional[Mistake]:
        """幂等查询：根据订正 request_id 返回已处理的结果。"""
        async with self.session_factory() as session:
            stmt = select(Mistake).where(
                Mistake.user_id == user_id,
                Mistake.correction_request_id == request_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_question(self, question_id: int) -> Optional[Question]:
        """查询单道题目。"""
        async with self.session_factory() as session:
            stmt = select(Question).where(Question.id == question_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_mistake_correction(
        self,
        mistake_id: int,
        answer: str,
        is_correct: bool,
        first_success: bool,
        request_id: str,
    ) -> Mistake:
        """更新错题订正结果。"""
        async with self.session_factory() as session:
            try:
                stmt = select(Mistake).where(Mistake.id == mistake_id)
                r = await session.execute(stmt)
                m = r.scalar_one_or_none()
                if not m:
                    raise ValueError(f"Mistake id={mistake_id} not found")
                m.correction_answer = answer
                m.correction_correct = is_correct
                m.correction_request_id = request_id
                m.corrected_at = datetime.now(_TZ)
                if is_correct:
                    m.correction_status = 'corrected'
                    if first_success:
                        m.first_correction_success = True
                # 下次复习时间在 service 层计算后设置
                await session.commit()
                await session.refresh(m)
                return m
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def set_mistake_next_review(self, mistake_id: int, next_review_at: datetime) -> None:
        """设置错题的下次复习时间。"""
        async with self.session_factory() as session:
            try:
                stmt = select(Mistake).where(Mistake.id == mistake_id)
                r = await session.execute(stmt)
                m = r.scalar_one_or_none()
                if m:
                    m.next_review_at = next_review_at
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def list_mistakes(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        subject: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
    ) -> Tuple[List[Mistake], int]:
        """分页查询错题列表。"""
        async with self.session_factory() as session:
            base = select(Mistake).where(Mistake.user_id == user_id)
            if status == 'review_due':
                today = date.today()
                base = base.where(
                    exists(
                        select(ReviewPlan.id).where(
                            ReviewPlan.mistake_id == Mistake.id,
                            ReviewPlan.user_id == user_id,
                            ReviewPlan.status == 'pending',
                            ReviewPlan.review_date <= today,
                        )
                    )
                )
            elif status:
                base = base.where(Mistake.correction_status == status)
            if subject == "__unclassified__":
                base = base.where((Mistake.subject.is_(None)) | (Mistake.subject == ""))
            elif subject:
                base = base.where(Mistake.subject == subject)
            if knowledge_point_name:
                base = base.where(Mistake.knowledge_point_name == knowledge_point_name)
            count_stmt = select(func.count()).select_from(base.subquery())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0
            stmt = (
                base
                .order_by(Mistake.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())
            return items, total

    async def list_mistake_subjects(self, user_id: int) -> List[str]:
        """Return all non-empty subject snapshots represented in the mistake book."""
        async with self.session_factory() as session:
            stmt = (
                select(Mistake.subject)
                .where(
                    Mistake.user_id == user_id,
                    Mistake.subject.is_not(None),
                    Mistake.subject != '',
                )
                .distinct()
                .order_by(Mistake.subject)
            )
            return list((await session.execute(stmt)).scalars().all())

    async def has_unclassified_mistakes(self, user_id: int) -> bool:
        """Whether legacy mistakes without a trustworthy subject snapshot exist."""
        async with self.session_factory() as session:
            stmt = select(Mistake.id).where(
                Mistake.user_id == user_id,
                (Mistake.subject.is_(None)) | (Mistake.subject == ""),
            ).limit(1)
            return (await session.execute(stmt)).scalar_one_or_none() is not None

    # ========== 复习计划 ==========

    async def create_review_plans(self, plans: List[ReviewPlan]) -> List[ReviewPlan]:
        """批量创建复习计划。"""
        async with self.session_factory() as session:
            try:
                session.add_all(plans)
                await session.commit()
                for p in plans:
                    await session.refresh(p)
                return plans
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_today_reviews(self, user_id: int) -> List[Tuple[ReviewPlan, Mistake]]:
        """查询今日到期且未完成的复习计划，关联错题信息。"""
        async with self.session_factory() as session:
            today = date.today()
            stmt = (
                select(ReviewPlan, Mistake)
                .join(Mistake, ReviewPlan.mistake_id == Mistake.id)
                .where(
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.review_date <= today,
                    ReviewPlan.status == 'pending',
                )
                .order_by(ReviewPlan.id)
            )
            result = await session.execute(stmt)
            return [(row.ReviewPlan, row.Mistake) for row in result.all()]

    async def reveal_review(
        self, review_id: int, user_id: int, mistake_id: int
    ) -> Optional[Tuple[ReviewPlan, Mistake, Optional[str]]]:
        """Mark one due review as revealed and return its answer context."""
        async with self.session_factory() as session:
            stmt = (
                select(ReviewPlan, Mistake, Question.analysis)
                .join(Mistake, ReviewPlan.mistake_id == Mistake.id)
                .outerjoin(Question, Mistake.question_id == Question.id)
                .where(
                    ReviewPlan.id == review_id,
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.mistake_id == mistake_id,
                    ReviewPlan.status == 'pending',
                    ReviewPlan.review_date <= date.today(),
                )
            )
            row = (await session.execute(stmt)).first()
            if not row:
                return None
            plan, mistake, analysis = row
            plan.status = 'revealed'
            plan.reviewed_at = datetime.now(_TZ)
            await session.commit()
            return plan, mistake, analysis

    async def get_review_progress(
        self, user_id: int, mistake_id: int, review_id: int
    ) -> Tuple[int, int, Optional[date]]:
        """Return current round, total standard rounds and next pending date."""
        async with self.session_factory() as session:
            rows = (
                await session.execute(
                    select(ReviewPlan.id, ReviewPlan.review_date, ReviewPlan.status)
                    .where(
                        ReviewPlan.user_id == user_id,
                        ReviewPlan.mistake_id == mistake_id,
                    )
                    .order_by(ReviewPlan.review_date, ReviewPlan.id)
                )
            ).all()
            current_round = next(
                (index for index, row in enumerate(rows, start=1) if row.id == review_id),
                0,
            )
            next_date = next(
                (
                    row.review_date
                    for row in rows
                    if row.status == 'pending' and row.id != review_id
                ),
                None,
            )
            return current_round, len(rows), next_date

    async def complete_review(self, review_id: int, user_id: int, mistake_id: int) -> bool:
        """仅在复习计划属于当前用户和错题时标记完成。"""
        async with self.session_factory() as session:
            try:
                stmt = select(ReviewPlan).where(
                    ReviewPlan.id == review_id,
                    ReviewPlan.user_id == user_id,
                    ReviewPlan.mistake_id == mistake_id,
                    ReviewPlan.status == 'pending',
                )
                r = await session.execute(stmt)
                plan = r.scalar_one_or_none()
                if not plan:
                    return False
                plan.status = 'completed'
                plan.reviewed_at = datetime.now(_TZ)
                await session.commit()
                return True
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def has_pending_review(self, review_id: int, user_id: int, mistake_id: int) -> bool:
        """校验待复习计划的归属，避免通过其他用户的 review_id 完成复习。"""
        async with self.session_factory() as session:
            stmt = select(ReviewPlan.id).where(
                ReviewPlan.id == review_id,
                ReviewPlan.user_id == user_id,
                ReviewPlan.mistake_id == mistake_id,
                ReviewPlan.status == 'pending',
            )
            return (await session.execute(stmt)).scalar_one_or_none() is not None


async def get_mastery_mapper() -> MasteryMapper:
    return MasteryMapper(AsyncSessionLocal)
