from datetime import date, datetime

from pydantic import BaseModel


class VipStatusResponse(BaseModel):
    is_vip: bool
    started_at: datetime | None
    expires_at: datetime | None


class FeatureUsageResponse(BaseModel):
    used: int
    limit: int | None
    remaining: int | None


class VipUsageResponse(BaseModel):
    date: date
    membership: str
    practice_generation: FeatureUsageResponse
    detailed_analysis: FeatureUsageResponse
    stage_report: FeatureUsageResponse


class PaymentOrderResponse(BaseModel):
    order_no: str
    plan: str
    amount: str
    status: str
    alipay_trade_no: str | None = None
    paid_at: datetime | None = None
    vip_expires_at: datetime | None = None
    created_at: datetime


class PaymentOrderPageResponse(BaseModel):
    items: list[PaymentOrderResponse]
    page: int
    page_size: int
    total: int
    pages: int


class AlipayFormResponse(BaseModel):
    order_no: str
    status: str
    payment_url: str
