from datetime import date, datetime

from pydantic import BaseModel


class PointAccountResponse(BaseModel):
    balance: int
    earned_total: int
    spent_total: int


class PointTransactionResponse(BaseModel):
    transaction_id: int
    business_type: str
    change: int
    balance_after: int
    description: str
    created_at: datetime


class PointTransactionPageResponse(BaseModel):
    items: list[PointTransactionResponse]
    page: int
    page_size: int
    total: int
    pages: int


class PointExchangeResponse(BaseModel):
    item_type: str
    target_id: int | None
    cost: int
    balance: int


class PointCheckInResponse(BaseModel):
    awarded: bool
    reason: str | None
    points: int
    balance: int | None = None


class PointTaskResponse(BaseModel):
    task_type: str
    title: str
    progress: int
    target: int
    reward_points: int
    claimed: bool


class PointTaskListResponse(BaseModel):
    date: date
    items: list[PointTaskResponse]
