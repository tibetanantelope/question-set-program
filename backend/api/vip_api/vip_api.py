from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse
from backend.middleware.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.model import get_db
from backend.model.user import User
from backend.schemas.response.base_response import ApiResponse, success
from backend.schemas.request.vip_request import VipOrderCreateRequest
from backend.schemas.response.vip_response import (
    AlipayFormResponse,
    PaymentOrderPageResponse,
    PaymentOrderResponse,
    VipStatusResponse,
    VipUsageResponse,
)
from backend.services.vip_service.payment_service import payment_service
from backend.services.vip_service.vip_service import vip_service

vip_router = APIRouter(prefix="/vip", tags=["vip"])
logger = get_logger(__name__)


@vip_router.post("/alipay/notify", response_class=PlainTextResponse)
async def alipay_notify(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """支付宝异步通知无需登录，以 RSA2 签名和订单数据作为信任边界。"""
    try:
        form = await request.form()
        await payment_service.handle_notification(db, dict(form))
        return "success"
    except Exception:
        logger.exception("支付宝异步通知处理失败")
        return "failure"


@vip_router.get("/status", response_model=ApiResponse[VipStatusResponse])
async def get_vip_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(await vip_service.get_status(db, current_user.id))


@vip_router.get("/usage", response_model=ApiResponse[VipUsageResponse])
async def get_vip_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(await vip_service.get_usage(db, current_user.id))


@vip_router.post("/orders", response_model=ApiResponse[PaymentOrderResponse])
async def create_vip_order(
    request: VipOrderCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Header(alias="X-Request-ID", min_length=1, max_length=64)],
):
    return success(
        await payment_service.create_order(
            db,
            user_id=current_user.id,
            plan=request.plan,
            request_id=request_id,
        )
    )


@vip_router.post("/orders/{order_no}/alipay", response_model=ApiResponse[AlipayFormResponse])
async def create_alipay_payment(
    order_no: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(
        await payment_service.create_payment_form(
            db, user_id=current_user.id, order_no=order_no
        )
    )


@vip_router.post("/orders/{order_no}/query", response_model=ApiResponse[PaymentOrderResponse])
async def query_alipay_payment(
    order_no: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(
        await payment_service.query_order(db, user_id=current_user.id, order_no=order_no)
    )


@vip_router.get("/orders/{order_no}", response_model=ApiResponse[PaymentOrderResponse])
async def get_vip_order(
    order_no: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(
        await payment_service.get_order(db, user_id=current_user.id, order_no=order_no)
    )


@vip_router.get("/orders", response_model=ApiResponse[PaymentOrderPageResponse])
async def get_vip_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return success(
        await payment_service.list_orders(
            db, user_id=current_user.id, page=page, page_size=page_size
        )
    )
