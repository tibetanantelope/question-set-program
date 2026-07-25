"""成员三：答题记录、掌握度、错题和复习计划的数据访问层"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, case
from sqlalchemy.exc import SQLAlchemyError

from backend.model import AsyncSessionLocal
from backend.model.mastery import AnswerRecord, KnowledgeMastery, Mistake, ReviewPlan

# 东八区
_TZ = timezone(timedelta(hours=8))


class MasteryMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

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
    ) -> Tuple[List[Mistake], int]:
        """分页查询错题列表。"""
        async with self.session_factory() as session:
            base = select(Mistake).where(Mistake.user_id == user_id)
            if status:
                base = base.where(Mistake.correction_status == status)
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
                    ReviewPlan.review_date == today,
                    ReviewPlan.status == 'pending',
                )
                .order_by(ReviewPlan.id)
            )
            result = await session.execute(stmt)
            return [(row.ReviewPlan, row.Mistake) for row in result.all()]

    async def complete_review(self, review_id: int) -> None:
        """标记复习计划为已完成。"""
        async with self.session_factory() as session:
            try:
                stmt = select(ReviewPlan).where(ReviewPlan.id == review_id)
                r = await session.execute(stmt)
                plan = r.scalar_one_or_none()
                if plan:
                    plan.status = 'completed'
                    plan.reviewed_at = datetime.now(_TZ)
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise


async def get_mastery_mapper() -> MasteryMapper:
    return MasteryMapper(AsyncSessionLocal)
