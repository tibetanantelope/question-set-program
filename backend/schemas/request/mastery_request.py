"""成员三：答题、掌握度、错题订正与复习 - 请求 Schema

字段严格对齐《智学伴接口与并行开发契约》第 9 节。
"""

from pydantic import BaseModel, Field


class CorrectionSubmitRequest(BaseModel):
    """提交错题订正 POST /mistakes/{mistake_id}/correction（请求头须含 X-Request-ID）"""
    answer: str = Field(..., min_length=1, description='订正答案')
