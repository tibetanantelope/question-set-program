from typing import Literal

from pydantic import BaseModel


class VipOrderCreateRequest(BaseModel):
    plan: Literal["vip_30_days"]
