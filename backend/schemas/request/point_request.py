from typing import Literal

from pydantic import BaseModel


class PointExchangeRequest(BaseModel):
    item_type: Literal["extra_practice", "detailed_analysis", "stage_report"]
    target_id: int | None = None
