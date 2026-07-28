"""向支付宝沙箱查账并补偿本地未完成的 VIP 订单。"""

import argparse
import asyncio

from sqlalchemy import select

from backend.model import AsyncSessionLocal, engine
from backend.model.payment_order import PaymentOrder
from backend.model.user import User
from backend.model.vip_info import VipInfo
from backend.services.vip_service.payment_service import payment_service


async def reconcile(username: str) -> None:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
        if user is None:
            raise RuntimeError(f"User not found: {username}")
        orders = (
            await db.execute(
                select(PaymentOrder)
                .where(
                    PaymentOrder.user_id == user.id,
                    PaymentOrder.status.in_(("pending", "paying")),
                )
                .order_by(PaymentOrder.created_at)
            )
        ).scalars().all()
        for order in orders:
            try:
                result = await payment_service.query_order(
                    db, user_id=user.id, order_no=order.order_no
                )
                print(order.order_no, "=>", result["status"])
            except Exception as exc:
                print(order.order_no, "=> ERROR:", type(exc).__name__, str(exc))
        vip = (
            await db.execute(select(VipInfo).where(VipInfo.user_id == user.id))
        ).scalar_one_or_none()
        paid_orders = (
            await db.execute(
                select(PaymentOrder.order_no).where(
                    PaymentOrder.user_id == user.id,
                    PaymentOrder.status == "paid",
                )
            )
        ).scalars().all()
        print("paid_orders=", list(paid_orders))
        print("vip_expires_at=", vip.expires_at if vip else None)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    asyncio.run(reconcile(args.username))
