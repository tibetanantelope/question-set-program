"""成员三：答题、掌握度、错题订正与复习 - 请求 Schema

字段严格对齐《智学伴接口与并行开发契约》第 9 节。
"""

from typing import Literal

from pydantic import BaseModel, Field


class CorrectionSubmitRequest(BaseModel):
    """提交错题订正 POST /mistakes/{mistake_id}/correction（请求头须含 X-Request-ID）"""
    answer: str = Field(..., min_length=1, description='订正答案')
    review_id: int | None = Field(None, gt=0, description='从复习计划提交时携带的复习计划ID')


class MistakeAnalysisRequest(BaseModel):
    """查看错题解析 POST /mistakes/{mistake_id}/analysis"""
    payment_method: Literal['basic', 'points', 'vip'] = Field(
        default='basic',
        description='basic 免费简单解析；points 积分兑换详细解析；vip 会员详细解析',
    )


class KnowledgeReviewCompleteRequest(BaseModel):
    knowledge_point_name: str = Field(..., min_length=1, max_length=128)
    subject: str | None = Field(None, max_length=32)
    review_mode: Literal['quick', 'full', 'advanced'] = 'full'
    answers: list[int] = Field(default_factory=list, max_length=10)
