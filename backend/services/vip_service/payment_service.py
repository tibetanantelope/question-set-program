import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.alipay_client import AlipaySandboxClient
from backend.core.exceptions import BusinessError
from backend.dao.payment_mapper import PaymentMapper
from backend.model.payment_order import PaymentOrder
from backend.model.vip_info import VipInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
VIP_PLAN = "vip_30_days"
VIP_AMOUNT = Decimal("19.90")
PAID_TRADE_STATUSES = {"TRADE_SUCCESS", "TRADE_FINISHED"}
CLOSED_TRADE_STATUSES = {"TRADE_CLOSED"}
ORDER_TTL = timedelta(hours=2)


class PaymentService:
    def __init__(self, mapper=None, alipay=None):
        self.mapper = mapper or PaymentMapper()
        self.alipay = alipay or AlipaySandboxClient()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)

    @staticmethod
    def _aware(value):
        if value is None:
            return None
        return value.replace(tzinfo=SHANGHAI_TZ) if value.tzinfo is None else value.astimezone(SHANGHAI_TZ)

    @classmethod
    def _order_data(cls, order: PaymentOrder) -> dict:
        return {
            "order_no": order.order_no,
            "plan": order.plan,
            "amount": str(order.amount),
            "status": order.status,
            "alipay_trade_no": order.alipay_trade_no,
            "paid_at": cls._aware(order.paid_at),
            "vip_expires_at": None,
            "created_at": cls._aware(order.created_at),
        }

    @staticmethod
    def _new_order_no(now: datetime) -> str:
        return f"ZXB{now:%Y%m%d%H%M%S}{secrets.randbelow(100_000_000):08d}"

    async def create_order(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan: str,
        request_id: str,
    ) -> dict:
        if plan != VIP_PLAN:
            raise BusinessError("INVALID_VIP_PLAN", "不支持的VIP套餐", 400)
        existing = await self.mapper.get_by_request_id(db, request_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
            return self._order_data(existing)

        now = self._now()
        order = PaymentOrder(
            order_no=self._new_order_no(now),
            user_id=user_id,
            request_id=request_id,
            plan=plan,
            amount=VIP_AMOUNT,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self.mapper.add(db, order)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_by_request_id(db, request_id)
            if existing is None or existing.user_id != user_id:
                raise
            order = existing
        return self._order_data(order)

    async def _owned_order(self, db, user_id: int, order_no: str, *, for_update=False):
        order = await self.mapper.get_order(db, order_no, for_update=for_update)
        if order is None or order.user_id != user_id:
            raise BusinessError("ORDER_NOT_FOUND", "订单不存在", 404)
        return order

    async def create_payment_form(self, db, *, user_id: int, order_no: str) -> dict:
        order = await self._owned_order(db, user_id, order_no, for_update=True)
        if order.status == "paid":
            raise BusinessError("ORDER_STATUS_CONFLICT", "订单已经支付", 409)
        if order.status in {"closed", "cancelled"}:
            raise BusinessError("ORDER_STATUS_CONFLICT", "订单已关闭", 409)
        payment_url = self.alipay.create_page_pay_url(
            order_no=order.order_no,
            amount=str(order.amount),
            subject="智学伴30天VIP会员",
        )
        order.status = "paying"
        await db.commit()
        return {
            "order_no": order.order_no,
            "status": order.status,
            "payment_url": payment_url,
        }

    async def _activate_paid_order(self, db, *, user_id: int, order_no: str, trade: dict):
        order = await self._owned_order(db, user_id, order_no, for_update=True)
        if trade.get("out_trade_no") != order.order_no:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝订单号校验失败", 400)
        try:
            paid_amount = Decimal(str(trade.get("total_amount")))
        except Exception as exc:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝支付金额无效", 400) from exc
        if paid_amount != order.amount:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝支付金额不一致", 400)
        if trade.get("trade_status") not in PAID_TRADE_STATUSES:
            raise BusinessError("ORDER_STATUS_CONFLICT", "支付宝订单尚未支付成功", 409)
        incoming_trade_no = trade.get("trade_no")
        if not incoming_trade_no:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝交易号缺失", 400)
        if order.alipay_trade_no and order.alipay_trade_no != incoming_trade_no:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝交易号与已确认订单不一致", 400)
        if order.status == "paid" and order.vip_applied_at is not None:
            info = await self.mapper.get_vip_info(db, user_id)
            data = self._order_data(order)
            data["vip_expires_at"] = self._aware(info.expires_at) if info else None
            return data

        now = self._now()
        info = await self.mapper.get_vip_info(db, user_id, for_update=True)
        if info is None:
            info = VipInfo(user_id=user_id, started_at=now, expires_at=now + timedelta(days=30))
            self.mapper.add(db, info)
        else:
            if not info.expires_at or info.expires_at <= now:
                info.started_at = now
                info.expires_at = now + timedelta(days=30)
            else:
                info.expires_at += timedelta(days=30)

        order.status = "paid"
        order.alipay_trade_no = incoming_trade_no
        order.paid_at = now
        order.vip_applied_at = now
        await db.commit()
        data = self._order_data(order)
        data["vip_expires_at"] = self._aware(info.expires_at)
        return data

    async def _close_order(self, db, order: PaymentOrder) -> dict:
        if order.status not in {"paid", "closed"}:
            now = self._now()
            order.status = "closed"
            order.closed_at = now
            order.updated_at = now
            await db.commit()
        return self._order_data(order)

    async def handle_notification(self, db, parameters: dict) -> dict:
        """验签并处理支付宝服务器异步通知。"""
        self.alipay.verify_notification(parameters)
        if parameters.get("app_id") != self.alipay.app_id:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝应用编号不一致", 400)
        order_no = parameters.get("out_trade_no")
        if not order_no:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝通知缺少商户订单号", 400)
        order = await self.mapper.get_order(db, order_no)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", "通知对应的订单不存在", 404)
        trade_status = parameters.get("trade_status")
        if trade_status in CLOSED_TRADE_STATUSES:
            return await self._close_order(db, order)
        if trade_status not in PAID_TRADE_STATUSES:
            return self._order_data(order)
        return await self._activate_paid_order(
            db,
            user_id=order.user_id,
            order_no=order_no,
            trade=parameters,
        )

    async def query_order(self, db, *, user_id: int, order_no: str) -> dict:
        order = await self._owned_order(db, user_id, order_no)
        if order.status == "paid" and order.vip_applied_at is not None:
            info = await self.mapper.get_vip_info(db, user_id)
            data = self._order_data(order)
            data["vip_expires_at"] = self._aware(info.expires_at) if info else None
            return data

        trade = await self.alipay.query_trade(order_no)
        if trade.get("code") != "10000":
            if trade.get("sub_code") in {"ACQ.TRADE_NOT_EXIST", "ACQ.TRADE_NOT_FOUND"}:
                if order.created_at and self._now() - order.created_at >= ORDER_TTL:
                    return await self._close_order(db, order)
                return self._order_data(order)
            raise BusinessError(
                "ALIPAY_QUERY_FAILED",
                trade.get("sub_msg") or trade.get("msg") or "支付宝订单查询失败",
                502,
            )
        if trade.get("trade_status") in CLOSED_TRADE_STATUSES:
            return await self._close_order(db, order)
        if trade.get("trade_status") not in PAID_TRADE_STATUSES:
            if order.created_at and self._now() - order.created_at >= ORDER_TTL:
                return await self._close_order(db, order)
            return self._order_data(order)
        return await self._activate_paid_order(
            db,
            user_id=user_id,
            order_no=order_no,
            trade=trade,
        )

    async def get_order(self, db, *, user_id: int, order_no: str) -> dict:
        order = await self._owned_order(db, user_id, order_no)
        data = self._order_data(order)
        if order.status == "paid":
            info = await self.mapper.get_vip_info(db, user_id)
            data["vip_expires_at"] = self._aware(info.expires_at) if info else None
        return data

    async def list_orders(self, db, *, user_id: int, page: int, page_size: int) -> dict:
        orders, total = await self.mapper.list_orders(db, user_id, page, page_size)
        return {
            "items": [self._order_data(order) for order in orders],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }


payment_service = PaymentService()
