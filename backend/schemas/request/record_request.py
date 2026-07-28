"""成员四请求模型"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class RecordQueryRequest(BaseModel):
    """历史学习记录查询参数（作为 query params 使用）"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    type: Optional[str] = Field(default=None, description='diagnosis/practice/correction/review/report')
    subject: Optional[str] = Field(default=None)
    date_from: Optional[str] = Field(default=None, description='YYYY-MM-DD')
    date_to: Optional[str] = Field(default=None, description='YYYY-MM-DD')


class GenerateReportRequest(BaseModel):
    """生成阶段性学情报告"""
    date_from: str = Field(..., description='YYYY-MM-DD')
    date_to: str = Field(..., description='YYYY-MM-DD')
    payment_method: str = Field(..., description='points 或 vip')

    @model_validator(mode='after')
    def validate_date_range(self):
        try:
            started = date.fromisoformat(self.date_from)
            ended = date.fromisoformat(self.date_to)
        except ValueError as exc:
            raise ValueError('日期必须为 YYYY-MM-DD 格式') from exc
        if started > ended:
            raise ValueError('开始日期不能晚于结束日期')
        if (ended - started).days > 365:
            raise ValueError('报告统计区间不能超过365天')
        return self


class PracticeCompletedEvent(BaseModel):
    """练习完成事件（由成员二/三调用）"""
    request_id: str
    user_id: int
    practice_id: int
    subject: Optional[str] = None
    knowledge_point_id: Optional[int] = None
    knowledge_point_name: Optional[str] = None
    question_count: int = 0
    correct_count: int = 0
    accuracy: float = 0.0
    is_valid: bool = False
    completed_at: Optional[datetime] = None


class CorrectionCompletedEvent(BaseModel):
    """订正完成事件（由成员三调用）"""
    request_id: str
    user_id: int
    mistake_id: int
    knowledge_point_id: Optional[int] = None
    knowledge_point_name: Optional[str] = None
    subject: Optional[str] = None
    first_success: bool = False
    completed_at: Optional[datetime] = None
