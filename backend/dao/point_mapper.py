from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.point_account import PointAccount
from backend.model.point_transaction import PointTransaction
from backend.model.learning_models import LearningRecord


class PointMapper:
    async def get_account(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> PointAccount | None:
        statement = select(PointAccount).where(PointAccount.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_account(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> PointAccount:
        account = await self.get_account(db, user_id, for_update=for_update)
        if account is not None:
            return account

        account = PointAccount(user_id=user_id)
        db.add(account)
        await db.flush()
        return account

    async def get_transaction_by_request_id(
        self,
        db: AsyncSession,
        request_id: str,
    ) -> PointTransaction | None:
        result = await db.execute(
            select(PointTransaction).where(PointTransaction.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def count_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        business_type: str,
        *,
        started_at=None,
        ended_at=None,
        business_id: str | None = None,
    ) -> int:
        statement = select(func.count(PointTransaction.id)).where(
            PointTransaction.user_id == user_id,
            PointTransaction.business_type == business_type,
        )
        if started_at is not None:
            statement = statement.where(PointTransaction.created_at >= started_at)
        if ended_at is not None:
            statement = statement.where(PointTransaction.created_at < ended_at)
        if business_id is not None:
            statement = statement.where(PointTransaction.business_id == business_id)
        result = await db.execute(statement)
        return int(result.scalar_one())

    async def count_transactions_by_type(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        started_at,
        ended_at,
    ) -> dict[str, int]:
        result = await db.execute(
            select(PointTransaction.business_type, func.count(PointTransaction.id))
            .where(
                PointTransaction.user_id == user_id,
                PointTransaction.created_at >= started_at,
                PointTransaction.created_at < ended_at,
            )
            .group_by(PointTransaction.business_type)
        )
        return {business_type: int(count) for business_type, count in result.all()}

    async def list_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[PointTransaction], int]:
        total_result = await db.execute(
            select(func.count(PointTransaction.id)).where(PointTransaction.user_id == user_id)
        )
        total = int(total_result.scalar_one())
        result = await db.execute(
            select(PointTransaction)
            .where(PointTransaction.user_id == user_id)
            .order_by(PointTransaction.created_at.desc(), PointTransaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_recent_learning_times(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        limit: int = 400,
    ) -> list:
        result = await db.execute(
            select(LearningRecord.occurred_at)
            .where(
                LearningRecord.user_id == user_id,
                LearningRecord.record_type.in_(("practice", "correction")),
            )
            .order_by(LearningRecord.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def add_transaction(self, db: AsyncSession, transaction: PointTransaction) -> None:
        db.add(transaction)
