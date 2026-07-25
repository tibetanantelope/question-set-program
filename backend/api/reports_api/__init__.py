"""成员四 API：学情报告"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse

from backend.api.dependencies import get_current_user
from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger
from backend.model.user import User
from backend.schemas.request.record_request import GenerateReportRequest
from backend.schemas.response.base_response import success
from backend.services.report_service import report_service

logger = get_logger(__name__)

reports_router = APIRouter(prefix="/reports", tags=["reports"])


async def _check_report_entitlement(
    user_id: int,
    payment_method: str,
    request_id: str,
) -> None:
    """
    校验报告生成权益（调用成员五 Service）。

    payment_method: "points"  → 扣 20 积分
                    "vip"     → VIP 直接通过

    成员五 Service 未就绪时跳过校验（开发阶段）。
    """
    if payment_method not in ("points", "vip"):
        raise BusinessError("INVALID_PAYMENT_METHOD", "支付方式只能是 points 或 vip", 422)

    try:
        from backend.services.vip_service import vip_service
    except (ImportError, AttributeError):
        logger.warning("VIP service not available, skipping entitlement check for report")
        return

    try:
        await vip_service.authorize_feature(
            user_id=user_id,
            feature="stage_report",
            payment_method=payment_method,
            request_id=request_id,
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.warning("VIP entitlement check failed (service may not be ready): %s", e)
        # 开发阶段不阻断，联调时去掉
        return


@reports_router.post("/stage")
async def generate_stage_report(
    body: GenerateReportRequest,
    user: User = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())

    # 权益校验
    await _check_report_entitlement(
        user_id=user.id,
        payment_method=body.payment_method,
        request_id=request_id,
    )

    data = await report_service.generate_report(
        user_id=user.id,
        date_from=body.date_from,
        date_to=body.date_to,
        request_id=request_id,
    )
    return success(data)


@reports_router.get("")
async def get_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    items, total, pages = await report_service.get_reports(
        user_id=user.id, page=page, page_size=page_size
    )
    return success({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    })


@reports_router.get("/{report_id}")
async def get_report_detail(
    report_id: int,
    user: User = Depends(get_current_user),
):
    data = await report_service.get_report_detail(user_id=user.id, report_id=report_id)
    return success(data)
