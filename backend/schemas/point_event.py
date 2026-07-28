from datetime import datetime

from pydantic import BaseModel, Field


class PointEvent(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)
    user_id: int = Field(gt=0)
    occurred_at: datetime


class PracticeCompletedEvent(PointEvent):
    practice_id: int | str
    is_valid: bool = True


class CorrectionCompletedEvent(PointEvent):
    mistake_id: int | str
    first_success: bool


class StreakCompletedEvent(PointEvent):
    streak_id: str = Field(min_length=1, max_length=64)
