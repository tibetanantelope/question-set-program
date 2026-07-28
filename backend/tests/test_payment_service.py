from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.exceptions import BusinessError
from backend.model.payment_order import PaymentOrder
from backend.model.vip_info import VipInfo
from backend.services.vip_service.payment_service import PaymentService


class StubPaymentMapper:
    def __init__(self, order=None, vip_info=None):
        self.order = order
        self.vip_info = vip_info
        self.added = []

    async def get_by_request_id(self, _db, request_id):
        if self.order and self.order.request_id == request_id:
            return self.order
        return None

    async def get_order(self, _db, order_no, *, for_update=False):
        if self.order and self.order.order_no == order_no:
            return self.order
        return None

    async def get_vip_info(self, _db, _user_id, *, for_update=False):
        return self.vip_info

    async def list_orders(self, _db, _user_id, _page, _page_size):
        return ([self.order] if self.order else []), (1 if self.order else 0)

    def add(self, _db, model):
        self.added.append(model)
        if isinstance(model, PaymentOrder):
            self.order = model
        if isinstance(model, VipInfo):
            self.vip_info = model


class StubAlipay:
    def __init__(self, trade=None):
        self.trade = trade or {}
        self.app_id = "sandbox-app-1"
        self.verified = []

    def create_page_pay_url(self, **kwargs):
        return f"https://sandbox.example/pay?order_no={kwargs['order_no']}"

    async def query_trade(self, _order_no):
        return self.trade

    def verify_notification(self, parameters):
        self.verified.append(parameters)


def make_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


def make_order(**overrides):
    values = {
        "order_no": "ZXB202607220001",
        "user_id": 7,
        "request_id": "order-request-1",
        "plan": "vip_30_days",
        "amount": Decimal("19.90"),
        "status": "paying",
        "created_at": datetime(2026, 7, 22, 12, 0),
    }
    values.update(overrides)
    return PaymentOrder(**values)


@pytest.mark.asyncio
async def test_create_order_is_idempotent():
    order = make_order(status="pending")
    mapper = StubPaymentMapper(order=order)
    db = make_db()

    result = await PaymentService(mapper, StubAlipay()).create_order(
        db,
        user_id=7,
        plan="vip_30_days",
        request_id="order-request-1",
    )

    assert result["order_no"] == order.order_no
    assert mapper.added == []
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_payment_form_marks_order_as_paying():
    order = make_order(status="pending")
    db = make_db()

    result = await PaymentService(StubPaymentMapper(order), StubAlipay()).create_payment_form(
        db, user_id=7, order_no=order.order_no
    )

    assert result["status"] == "paying"
    assert order.status == "paying"
    assert result["payment_url"].startswith("https://sandbox.example/pay")
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_paid_query_opens_vip_for_thirty_days():
    now = datetime(2026, 7, 22, 12, 0)
    order = make_order()
    trade = {
        "code": "10000",
        "out_trade_no": order.order_no,
        "trade_no": "20260722220001",
        "total_amount": "19.90",
        "trade_status": "TRADE_SUCCESS",
    }
    mapper = StubPaymentMapper(order)
    service = PaymentService(mapper, StubAlipay(trade))
    service._now = lambda: now
    db = make_db()

    result = await service.query_order(db, user_id=7, order_no=order.order_no)

    assert result["status"] == "paid"
    assert mapper.vip_info.started_at == now
    assert mapper.vip_info.expires_at == now + timedelta(days=30)
    assert order.vip_applied_at == now
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_amount_mismatch_never_opens_vip():
    order = make_order()
    trade = {
        "code": "10000",
        "out_trade_no": order.order_no,
        "trade_no": "20260722220001",
        "total_amount": "0.01",
        "trade_status": "TRADE_SUCCESS",
    }
    mapper = StubPaymentMapper(order)
    db = make_db()

    with pytest.raises(BusinessError) as exc_info:
        await PaymentService(mapper, StubAlipay(trade)).query_order(
            db, user_id=7, order_no=order.order_no
        )

    assert exc_info.value.code == "PAYMENT_VERIFY_FAILED"
    assert mapper.vip_info is None
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_paid_query_does_not_extend_vip_again():
    expires_at = datetime(2026, 8, 21, 12, 0)
    info = VipInfo(user_id=7, started_at=datetime(2026, 7, 22, 12, 0), expires_at=expires_at)
    order = make_order(
        status="paid",
        paid_at=datetime(2026, 7, 22, 12, 0),
        vip_applied_at=datetime(2026, 7, 22, 12, 0),
    )
    mapper = StubPaymentMapper(order, info)
    db = make_db()

    result = await PaymentService(mapper, StubAlipay()).query_order(
        db, user_id=7, order_no=order.order_no
    )

    assert result["vip_expires_at"].replace(tzinfo=None) == expires_at
    assert info.expires_at == expires_at
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_order():
    order = make_order(user_id=8)

    with pytest.raises(BusinessError) as exc_info:
        await PaymentService(StubPaymentMapper(order), StubAlipay()).get_order(
            make_db(), user_id=7, order_no=order.order_no
        )

    assert exc_info.value.code == "ORDER_NOT_FOUND"


@pytest.mark.asyncio
async def test_active_vip_renewal_extends_from_existing_expiry():
    now = datetime(2026, 7, 22, 12, 0)
    current_expiry = datetime(2026, 8, 10, 12, 0)
    info = VipInfo(user_id=7, started_at=datetime(2026, 7, 1), expires_at=current_expiry)
    order = make_order()
    trade = {
        "code": "10000", "out_trade_no": order.order_no,
        "trade_no": "20260722220002", "total_amount": "19.90",
        "trade_status": "TRADE_SUCCESS",
    }
    mapper = StubPaymentMapper(order, info)
    service = PaymentService(mapper, StubAlipay(trade))
    service._now = lambda: now

    result = await service.query_order(make_db(), user_id=7, order_no=order.order_no)

    assert info.expires_at == current_expiry + timedelta(days=30)
    assert result["vip_expires_at"].replace(tzinfo=None) == info.expires_at


@pytest.mark.asyncio
async def test_paid_notification_is_verified_and_activates_vip():
    now = datetime(2026, 7, 22, 12, 0)
    order = make_order()
    alipay = StubAlipay()
    mapper = StubPaymentMapper(order)
    service = PaymentService(mapper, alipay)
    service._now = lambda: now
    notification = {
        "app_id": alipay.app_id,
        "out_trade_no": order.order_no,
        "trade_no": "20260722220003",
        "total_amount": "19.90",
        "trade_status": "TRADE_SUCCESS",
        "sign": "verified-by-stub",
        "sign_type": "RSA2",
    }

    result = await service.handle_notification(make_db(), notification)

    assert alipay.verified == [notification]
    assert result["status"] == "paid"
    assert mapper.vip_info.expires_at == now + timedelta(days=30)


@pytest.mark.asyncio
async def test_notification_app_id_mismatch_never_activates_vip():
    order = make_order()
    alipay = StubAlipay()
    mapper = StubPaymentMapper(order)
    notification = {
        "app_id": "another-app",
        "out_trade_no": order.order_no,
        "trade_no": "20260722220004",
        "total_amount": "19.90",
        "trade_status": "TRADE_SUCCESS",
    }

    with pytest.raises(BusinessError) as exc:
        await PaymentService(mapper, alipay).handle_notification(make_db(), notification)

    assert exc.value.code == "PAYMENT_VERIFY_FAILED"
    assert mapper.vip_info is None


@pytest.mark.asyncio
async def test_trade_closed_updates_local_order():
    order = make_order()
    trade = {
        "code": "10000",
        "out_trade_no": order.order_no,
        "trade_status": "TRADE_CLOSED",
    }
    service = PaymentService(StubPaymentMapper(order), StubAlipay(trade))
    now = datetime(2026, 7, 22, 15, 0)
    service._now = lambda: now

    result = await service.query_order(make_db(), user_id=7, order_no=order.order_no)

    assert result["status"] == "closed"
    assert order.closed_at == now


@pytest.mark.asyncio
async def test_notify_endpoint_returns_exact_success(monkeypatch):
    from backend.api.vip_api.vip_api import alipay_notify
    from backend.api.vip_api import vip_api as module

    request = SimpleNamespace(form=AsyncMock(return_value={
        "out_trade_no": "ZXB202607220001",
        "trade_status": "TRADE_SUCCESS",
    }))
    handler = AsyncMock(return_value={"status": "paid"})
    monkeypatch.setattr(module.payment_service, "handle_notification", handler)
    db = make_db()

    response = await alipay_notify(request=request, db=db)

    assert response == "success"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_endpoint_returns_failure_for_retry(monkeypatch):
    from backend.api.vip_api.vip_api import alipay_notify
    from backend.api.vip_api import vip_api as module

    request = SimpleNamespace(form=AsyncMock(return_value={"sign": "invalid"}))
    handler = AsyncMock(side_effect=BusinessError("PAYMENT_VERIFY_FAILED", "bad", 400))
    monkeypatch.setattr(module.payment_service, "handle_notification", handler)

    response = await alipay_notify(request=request, db=make_db())

    assert response == "failure"
