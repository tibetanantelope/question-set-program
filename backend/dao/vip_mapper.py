from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.usage_record import UsageRecord
from backend.model.point_transaction import PointTransaction
from backend.model.user import User
from backend.model.vip_info import VipInfo


class VipMapper:
    async def lock_user(self, db: AsyncSession, user_id: int) -> None:
        result = await db.execute(select(User.id).where(User.id == user_id).with_for_update())
        if result.scalar_one_or_none() is None:
            raise ValueError("user not found")

    async def get_vip_info(self, db: AsyncSession, user_id: int) -> VipInfo | None:
        result = await db.execute(select(VipInfo).where(VipInfo.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_usage_by_request_id(
        self,
        db: AsyncSession,
        request_id: str,
    ) -> UsageRecord | None:
        result = await db.execute(
            select(UsageRecord).where(UsageRecord.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def count_usage(
        self,
        db: AsyncSession,
        user_id: int,
        usage_date: date,
        feature: str,
        *,
        usage_source: str | None = None,
    ) -> int:
        statement = select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.usage_date == usage_date,
            UsageRecord.feature == feature,
        )
        if usage_source is not None:
            statement = statement.where(UsageRecord.usage_source == usage_source)
        result = await db.execute(statement)
        return int(result.scalar_one())

    async def count_available_extra_practices(
        self,
        db: AsyncSession,
        user_id: int,
        usage_date: date,
    ) -> int:
        """返回当天已兑换但尚未在成功出题后核销的额外练习次数。"""
        exchanged_result = await db.execute(
            select(func.count(PointTransaction.id)).where(
                PointTransaction.user_id == user_id,
                PointTransaction.business_type == "exchange_extra_practice",
                func.date(PointTransaction.created_at) == usage_date,
            )
        )
        consumed_result = await db.execute(
            select(func.count(UsageRecord.id)).where(
                UsageRecord.user_id == user_id,
                UsageRecord.usage_date == usage_date,
                UsageRecord.feature == "practice_generation",
                UsageRecord.usage_source == "points",
            )
        )
        return max(
            int(exchanged_result.scalar_one()) - int(consumed_result.scalar_one()),
            0,
        )

    async def count_extra_practice_exchanges(
        self,
        db: AsyncSession,
        user_id: int,
        usage_date: date,
    ) -> int:
        """统计当天兑换的额外练习次数，用于展示扩展后的今日额度。"""
        result = await db.execute(
            select(func.count(PointTransaction.id)).where(
                PointTransaction.user_id == user_id,
                PointTransaction.business_type == "exchange_extra_practice",
                func.date(PointTransaction.created_at) == usage_date,
            )
        )
        return int(result.scalar_one())

    def add_usage(self, db: AsyncSession, usage: UsageRecord) -> None:
        db.add(usage)
