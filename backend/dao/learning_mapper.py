"""成员二：智能诊断、练习与题目的数据访问层"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.model import AsyncSessionLocal
from backend.model.learning import LearningSession, Diagnosis, Practice, Question


class LearningMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

    # ========== 学习会话 ==========

    async def create_learning_session(self, user_id: int, session_key: Optional[str]) -> LearningSession:
        async with self.session_factory() as session:
            try:
                s = LearningSession(user_id=user_id, session_key=session_key, status='active')
                session.add(s)
                await session.commit()
                await session.refresh(s)
                return s
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ========== 诊断 ==========

    async def create_diagnosis(self, diagnosis: Diagnosis) -> Diagnosis:
        async with self.session_factory() as session:
            try:
                session.add(diagnosis)
                await session.commit()
                await session.refresh(diagnosis)
                return diagnosis
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_diagnosis(self, diagnosis_id: int, user_id: int) -> Optional[Diagnosis]:
        async with self.session_factory() as session:
            stmt = select(Diagnosis).where(
                Diagnosis.id == diagnosis_id,
                Diagnosis.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # ========== 练习 ==========

    async def get_practice_by_request_id(self, user_id: int, request_id: str) -> Optional[Practice]:
        """幂等查询：根据 request_id 返回已存在的练习。"""
        async with self.session_factory() as session:
            stmt = select(Practice).where(
                Practice.user_id == user_id,
                Practice.request_id == request_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_practice_with_questions(
        self, practice: Practice, questions: List[Question]
    ) -> Practice:
        """在同一事务内创建练习组及其题目。"""
        async with self.session_factory() as session:
            try:
                session.add(practice)
                await session.flush()  # 获取 practice.id
                for q in questions:
                    q.practice_id = practice.id
                    session.add(q)
                await session.commit()
                await session.refresh(practice)
                return practice
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_latest_completed_practice(
        self, user_id: int, knowledge_point_id: Optional[int]
    ) -> Optional[Practice]:
        """查询该用户（指定知识点）最近一次已完成的练习，用于难度衔接。"""
        async with self.session_factory() as session:
            stmt = select(Practice).where(
                Practice.user_id == user_id,
                Practice.status == 'completed',
            )
            if knowledge_point_id is not None:
                stmt = stmt.where(Practice.knowledge_point_id == knowledge_point_id)
            stmt = stmt.order_by(Practice.id.desc()).limit(1)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_practice(self, practice_id: int, user_id: int) -> Optional[Practice]:
        async with self.session_factory() as session:
            stmt = select(Practice).where(
                Practice.id == practice_id,
                Practice.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_practice_result(
        self, practice_id: int, correct_count: int, accuracy: float
    ) -> None:
        async with self.session_factory() as session:
            try:
                stmt = select(Practice).where(Practice.id == practice_id)
                r = await session.execute(stmt)
                p = r.scalar_one_or_none()
                if p:
                    p.correct_count = correct_count
                    p.accuracy = accuracy
                    p.status = 'completed'
                    p.is_valid = True
                    p.submitted_at = datetime.now()
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ========== 题目 ==========

    async def get_questions(self, practice_id: int) -> List[Question]:
        async with self.session_factory() as session:
            stmt = (
                select(Question)
                .where(Question.practice_id == practice_id)
                .order_by(Question.question_order)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_question(self, question_id: int, practice_id: int) -> Optional[Question]:
        async with self.session_factory() as session:
            stmt = select(Question).where(
                Question.id == question_id,
                Question.practice_id == practice_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_question_analysis(
        self,
        question_id: int,
        user_answer: str,
        is_correct: bool,
        error_type: Optional[str],
        error_description: Optional[str],
        next_suggestion: Optional[str],
    ) -> None:
        async with self.session_factory() as session:
            try:
                stmt = select(Question).where(Question.id == question_id)
                r = await session.execute(stmt)
                q = r.scalar_one_or_none()
                if q:
                    q.user_answer = user_answer
                    q.is_correct = is_correct
                    q.error_type = error_type
                    q.error_description = error_description
                    q.next_suggestion = next_suggestion
                    q.answered_at = datetime.now()
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise


async def get_learning_mapper() -> LearningMapper:
    return LearningMapper(AsyncSessionLocal)
