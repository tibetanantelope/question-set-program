"""成员三（第二阶段）：题库管理数据访问层"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, update, delete, or_
from sqlalchemy.exc import SQLAlchemyError

from backend.model import AsyncSessionLocal
from backend.model.learning import Question, KnowledgePoint

_TZ = timezone(timedelta(hours=8))


class QuestionBankMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

    # ========== 题目 ==========

    async def list_questions(
        self,
        keyword: Optional[str] = None,
        subject: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        standalone_only: bool = False,
    ) -> Tuple[List[Question], int]:
        """分页查询题库题目。standalone_only=True 只查独立题目。"""
        async with self.session_factory() as session:
            base = select(Question)
            if standalone_only:
                base = base.where(Question.practice_id.is_(None))
            if keyword:
                base = base.where(Question.content.contains(keyword))
            if subject:
                base = base.where(Question.subject == subject)
            if knowledge_point_name:
                base = base.where(Question.knowledge_point_name == knowledge_point_name)
            if difficulty:
                base = base.where(Question.difficulty == difficulty)
            if status:
                base = base.where(Question.status == status)
            if review_status:
                base = base.where(Question.review_status == review_status)

            count_stmt = select(func.count()).select_from(base.subquery())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0

            stmt = (
                base.order_by(Question.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())
            return items, total

    async def get_question(self, question_id: int) -> Optional[Question]:
        async with self.session_factory() as session:
            stmt = select(Question).where(Question.id == question_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_question(self, q: Question) -> Question:
        async with self.session_factory() as session:
            try:
                session.add(q)
                await session.commit()
                await session.refresh(q)
                return q
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def update_question(self, question_id: int, updates: dict) -> Question:
        async with self.session_factory() as session:
            try:
                stmt = select(Question).where(Question.id == question_id)
                r = await session.execute(stmt)
                q = r.scalar_one_or_none()
                if not q:
                    raise ValueError(f"Question id={question_id} not found")
                for key, value in updates.items():
                    if hasattr(q, key):
                        setattr(q, key, value)
                await session.commit()
                await session.refresh(q)
                return q
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def delete_question(self, question_id: int) -> None:
        async with self.session_factory() as session:
            try:
                stmt = select(Question).where(Question.id == question_id)
                r = await session.execute(stmt)
                q = r.scalar_one_or_none()
                if q:
                    await session.delete(q)
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def update_question_stats(
        self, question_id: int, is_correct: bool
    ) -> None:
        """更新题目使用统计。"""
        async with self.session_factory() as session:
            try:
                stmt = select(Question).where(Question.id == question_id)
                r = await session.execute(stmt)
                q = r.scalar_one_or_none()
                if q:
                    q.usage_count = (q.usage_count or 0) + 1
                    if is_correct:
                        q.total_correct = (q.total_correct or 0) + 1
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ========== 选题：为练习出题 ==========

    async def fetch_published_questions(
        self,
        knowledge_point_name: Optional[str] = None,
        subject: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 5,
    ) -> List[Question]:
        """从已上架独立题库中随机抽取题目（知识点模糊匹配）。"""
        async with self.session_factory() as session:
            base = select(Question).where(
                Question.review_status == 'published',
                Question.status == 'approved',
                Question.practice_id.is_(None),
            )
            # 知识点模糊匹配：精确命中 或 包含关系（支持"牛顿第二定律-应用"等带后缀名称）
            if knowledge_point_name:
                base = base.where(
                    or_(
                        Question.knowledge_point_name == knowledge_point_name,
                        Question.knowledge_point_name.contains(knowledge_point_name),
                    )
                )
            if subject:
                base = base.where(Question.subject == subject)
            if difficulty:
                base = base.where(Question.difficulty == difficulty)

            base = base.order_by(func.rand()).limit(limit)
            result = await session.execute(base)
            return list(result.scalars().all())

    # ========== 知识点 ==========

    async def list_knowledge_points(
        self,
        subject: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[KnowledgePoint], int]:
        async with self.session_factory() as session:
            base = select(KnowledgePoint)
            if subject:
                base = base.where(KnowledgePoint.subject == subject)
            if keyword:
                base = base.where(KnowledgePoint.name.contains(keyword))

            count_stmt = select(func.count()).select_from(base.subquery())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0

            stmt = base.order_by(KnowledgePoint.subject, KnowledgePoint.id).offset((page - 1) * page_size).limit(page_size)
            result = await session.execute(stmt)
            items = list(result.scalars().all())
            return items, total

    async def get_knowledge_point(self, kp_id: int) -> Optional[KnowledgePoint]:
        async with self.session_factory() as session:
            stmt = select(KnowledgePoint).where(KnowledgePoint.id == kp_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_knowledge_point(self, kp: KnowledgePoint) -> KnowledgePoint:
        async with self.session_factory() as session:
            try:
                session.add(kp)
                await session.commit()
                await session.refresh(kp)
                return kp
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_subjects_list(self) -> List[str]:
        """返回所有有题目的学科列表。"""
        async with self.session_factory() as session:
            stmt = select(Question.subject).where(
                Question.subject.isnot(None),
            ).distinct()
            result = await session.execute(stmt)
            return sorted([r[0] for r in result.all() if r[0]])


async def get_question_bank_mapper() -> QuestionBankMapper:
    return QuestionBankMapper(AsyncSessionLocal)
