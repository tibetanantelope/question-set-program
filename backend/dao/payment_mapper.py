from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.payment_order import PaymentOrder
from backend.model.vip_info import VipInfo


class PaymentMapper:
    async def get_by_request_id(self, db: AsyncSession, request_id: str):
        result = await db.execute(
            select(PaymentOrder).where(PaymentOrder.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_order(
        self,
        db: AsyncSession,
        order_no: str,
        *,
        for_update: bool = False,
    ):
        statement = select(PaymentOrder).where(PaymentOrder.order_no == order_no)
        if for_update:
            statement = statement.with_for_update()
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def list_orders(self, db, user_id: int, page: int, page_size: int):
        total_result = await db.execute(
            select(func.count(PaymentOrder.id)).where(PaymentOrder.user_id == user_id)
        )
        total = int(total_result.scalar_one())
        result = await db.execute(
            select(PaymentOrder)
            .where(PaymentOrder.user_id == user_id)
            .order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_vip_info(self, db, user_id: int, *, for_update: bool = False):
        statement = select(VipInfo).where(VipInfo.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    def add(self, db, model) -> None:
        db.add(model)
