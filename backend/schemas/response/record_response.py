"""成员四响应模型"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── 分页模型 ───
class PaginatedItems(BaseModel):
    items: List[Any] = []
    page: int = 1
    page_size: int = 20
    total: int = 0
    pages: int = 0


# ─── 学习记录 ───
class LearningRecordItem(BaseModel):
    record_id: int
    record_type: str
    title: str
    subject: Optional[str] = None
    knowledge_point_name: Optional[str] = None
    question_count: int = 0
    correct_count: int = 0
    accuracy: Optional[float] = None
    mastery_change: int = 0
    occurred_at: str = ""


# ─── 首页推荐 ───
class RecommendItem(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    target_id: Optional[int] = None
    priority: int = 1


class HomeRecommendationResponse(BaseModel):
    primary: Optional[RecommendItem] = None
    secondary: List[RecommendItem] = []


# ─── 今日计划 ───
class PlanTask(BaseModel):
    task_type: str
    title: str
    status: str = "pending"


class TodayPlanResponse(BaseModel):
    date: str = ""
    target_groups: int = 0
    completed_groups: int = 0
    completed: bool = False
    tasks: List[PlanTask] = []


# ─── 站内提醒 ───
class NotificationItem(BaseModel):
    notification_id: int
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool = False
    created_at: str = ""


# ─── 学情报告 ───
class StageReportResponse(BaseModel):
    report_id: int
    date_from: str = ""
    date_to: str = ""
    practice_count: int = 0
    question_count: int = 0
    accuracy: float = 0.0
    mastery_change: int = 0
    frequent_error_type: Optional[str] = None
    weak_points: List[str] = []
    suggestion: Optional[str] = None
    created_at: str = ""


class ReportListItem(BaseModel):
    report_id: int
    date_from: str = ""
    date_to: str = ""
    practice_count: int = 0
    accuracy: Optional[float] = None
    created_at: str = ""
