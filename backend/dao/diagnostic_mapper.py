from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from backend.model import AsyncSessionLocal
from backend.model.diagnostic import DiagnosticSession, DiagnosticAnswer


class DiagnosticMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

    # ========== 诊断会话 ==========

    async def create_session(self, user_id: int, question_count: int) -> DiagnosticSession:
        async with self.session_factory() as session:
            try:
                s = DiagnosticSession(user_id=user_id, question_count=question_count, status='in_progress')
                session.add(s)
                await session.commit()
                await session.refresh(s)
                return s
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_session(self, diagnostic_id: int, user_id: int) -> Optional[DiagnosticSession]:
        """查询指定用户的诊断会话。"""
        async with self.session_factory() as session:
            stmt = select(DiagnosticSession).where(
                DiagnosticSession.id == diagnostic_id,
                DiagnosticSession.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_latest_in_progress(self, user_id: int) -> Optional[DiagnosticSession]:
        """获取用户最新进行中的诊断会话。"""
        async with self.session_factory() as session:
            stmt = (
                select(DiagnosticSession)
                .where(DiagnosticSession.user_id == user_id, DiagnosticSession.status == 'in_progress')
                .order_by(DiagnosticSession.id.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def update_session_status(self, diagnostic_id: int, status: str) -> None:
        """更新诊断会话状态。"""
        async with self.session_factory() as session:
            from datetime import datetime
            try:
                stmt = select(DiagnosticSession).where(DiagnosticSession.id == diagnostic_id)
                r = await session.execute(stmt)
                s = r.scalar_one_or_none()
                if s:
                    s.status = status
                    if status in ('completed', 'skipped'):
                        s.completed_at = datetime.now()
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ========== 诊断答案 ==========

    async def save_answers(self, diagnostic_id: int, answers: List[DiagnosticAnswer]) -> List[DiagnosticAnswer]:
        async with self.session_factory() as session:
            try:
                session.add_all(answers)
                await session.commit()
                # 逐条刷新
                for a in answers:
                    await session.refresh(a)
                return answers
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def get_answers(self, diagnostic_id: int) -> List[DiagnosticAnswer]:
        async with self.session_factory() as session:
            stmt = select(DiagnosticAnswer).where(DiagnosticAnswer.diagnostic_id == diagnostic_id).order_by(DiagnosticAnswer.question_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_answer(self, answer_id: int, user_answer: str, is_correct: bool) -> None:
        async with self.session_factory() as session:
            try:
                stmt = select(DiagnosticAnswer).where(DiagnosticAnswer.id == answer_id)
                r = await session.execute(stmt)
                a = r.scalar_one_or_none()
                if a:
                    a.user_answer = user_answer
                    a.is_correct = is_correct
                    await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise


async def get_diagnostic_mapper() -> DiagnosticMapper:
    return DiagnosticMapper(AsyncSessionLocal)
