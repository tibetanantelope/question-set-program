"""成员三：答题、掌握度、错题订正与复习 - 响应 Schema

字段严格对齐《智学伴接口与并行开发契约》第 5、9 节。
"""

from typing import List, Optional
from datetime import date

from pydantic import BaseModel, Field


# ==================== 公共结构（第 5 节） ====================

class MasterySummary(BaseModel):
    """知识点掌握摘要 - 对齐契约 5.2"""
    knowledge_point_id: int = Field(description='知识点ID')
    knowledge_point_name: str = Field(description='知识点名称')
    mastery_score: int = Field(description='掌握度: 0-100')
    learning_status: str = Field(description='weak/consolidating/mastered')
    answer_count: int = Field(description='累计答题次数')
    correct_count: int = Field(description='累计答对次数')
    last_studied_at: Optional[str] = Field(None, description='最近一次学习时间（ISO 8601）')


# ==================== 9.1 知识点掌握查询 ====================

class MasteryListResponse(BaseModel):
    """分页掌握度列表"""
    items: List[MasterySummary] = Field(default_factory=list)
    page: int = Field(1)
    page_size: int = Field(20)
    total: int = Field(0)
    pages: int = Field(0)


# ==================== 9.2 掌握度趋势 ====================

class TrendPoint(BaseModel):
    """趋势数据点"""
    date: str = Field(description='日期 YYYY-MM-DD')
    score: int = Field(description='当日掌握度')


class TrendResponse(BaseModel):
    """掌握度趋势"""
    current_score: int = Field(description='当前掌握度')
    change: int = Field(description='时间段内变化值')
    points: List[TrendPoint] = Field(default_factory=list, description='每日数据点')


# ==================== 9.3 错题查询 ====================

class MistakeItem(BaseModel):
    """错题条目"""
    mistake_id: int = Field(description='错题ID')
    question_id: Optional[int] = Field(None, description='关联题目ID')
    question_content: Optional[str] = Field(None, description='题目内容')
    user_answer: Optional[str] = Field(None, description='学生错误答案')
    standard_answer: Optional[str] = Field(None, description='标准答案')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')
    error_type: Optional[str] = Field(None, description='knowledge/calculation/reading/method')
    correction_status: str = Field(description='pending/corrected/review_due')
    next_review_at: Optional[str] = Field(None, description='下一次复习到期时间（ISO 8601）')
    created_at: Optional[str] = Field(None, description='错题生成时间（ISO 8601）')


class MistakeListResponse(BaseModel):
    """分页错题列表"""
    items: List[MistakeItem] = Field(default_factory=list)
    page: int = Field(1)
    page_size: int = Field(20)
    total: int = Field(0)
    pages: int = Field(0)


# ==================== 9.4 错题订正 ====================

class CorrectionResponse(BaseModel):
    """订正结果"""
    mistake_id: int = Field(description='错题ID')
    is_correct: bool = Field(description='订正答案是否正确')
    correction_status: str = Field(description='corrected')
    first_success: bool = Field(description='是否为首次订正成功')
    review_dates: List[str] = Field(default_factory=list, description='后续复习日期列表 YYYY-MM-DD')


# ==================== 9.5 今日复习 ====================

class ReviewItem(BaseModel):
    """今日到期复习项"""
    review_id: int = Field(description='复习计划ID')
    mistake_id: int = Field(description='关联错题ID')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')
    question_content: Optional[str] = Field(None, description='题目内容（冗余）')
    standard_answer: Optional[str] = Field(None, description='标准答案')
    user_answer: Optional[str] = Field(None, description='原始错误答案')
    error_type: Optional[str] = Field(None, description='错因类型')
    review_date: str = Field(description='复习日期 YYYY-MM-DD')
    status: str = Field(description='pending/completed')


# ==================== Service 内部事件（第 5.4 / 5.6 节） ====================

class AnswerResultEvent(BaseModel):
    """答题结果事件 - 成员二调用成员三的契约"""
    request_id: str = Field(description='幂等标识')
    user_id: int = Field(description='用户ID')
    practice_id: int = Field(description='练习组ID')
    question_id: int = Field(description='题目ID')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')
    difficulty: str = Field('easy', description='easy/medium/hard')
    is_correct: bool = Field(description='是否正确')
    error_type: Optional[str] = Field(None, description='knowledge/calculation/reading/method')
    answered_at: str = Field(description='答题时间（ISO 8601）')


class CorrectionCompletedEvent(BaseModel):
    """错题订正完成事件 - 成员三发给成员五"""
    request_id: str = Field(description='幂等标识')
    user_id: int = Field(description='用户ID')
    mistake_id: int = Field(description='错题ID')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    first_success: bool = Field(description='是否为首次订正成功')
    completed_at: str = Field(description='完成时间（ISO 8601）')
