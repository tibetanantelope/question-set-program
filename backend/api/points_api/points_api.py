from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.model import get_db
from backend.model.user import User
from backend.schemas.request.point_request import PointExchangeRequest
from backend.schemas.response.base_response import ApiResponse, success
from backend.schemas.response.point_response import (
    PointAccountResponse,
    PointCheckInResponse,
    PointExchangeResponse,
    PointTaskListResponse,
    PointTransactionPageResponse,
)
from backend.services.point_service.point_service import point_service
from backend.core.exceptions import BusinessError

points_router = APIRouter(prefix="/points", tags=["points"])


@points_router.get("/account", response_model=ApiResponse[PointAccountResponse])
async def get_point_account(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(await point_service.get_account(db, current_user.id))


@points_router.get(
    "/transactions",
    response_model=ApiResponse[PointTransactionPageResponse],
)
async def get_point_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    data = await point_service.list_transactions(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return success(data)


@points_router.get("/tasks", response_model=ApiResponse[PointTaskListResponse])
async def get_point_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success(await point_service.get_tasks(db, current_user.id))


@points_router.post("/check-in", response_model=ApiResponse[PointCheckInResponse])
async def check_in(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Header(alias="X-Request-ID", min_length=1, max_length=64)],
):
    return success(
        await point_service.check_in(
            db,
            user_id=current_user.id,
            request_id=request_id,
        )
    )


@points_router.post("/exchanges", response_model=ApiResponse[PointExchangeResponse])
async def exchange_points(
    request: PointExchangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Header(alias="X-Request-ID", min_length=1, max_length=64)],
):
    if request.item_type in {"detailed_analysis", "stage_report"}:
        raise BusinessError(
            "USE_FEATURE_ENDPOINT",
            "该能力需要在对应功能页面按次使用，系统会在成功请求时扣除积分",
            409,
        )
    data = await point_service.exchange(
        db,
        user_id=current_user.id,
        item_type=request.item_type,
        target_id=request.target_id,
        request_id=request_id,
    )
    return success(data)
