from typing import Optional

from pydantic import BaseModel, Field


class StudentProfileSummary(BaseModel):
    """画像摘要，用作嵌套结构或独立返回。"""
    stage: str = Field(description='学段')
    grade: str = Field(description='年级')
    subject: str = Field(description='学科或课程')
    learning_goal: str = Field(description='学习目标')
    weekly_study_days: int = Field(description='每周学习天数')
    daily_target_groups: int = Field(description='每日目标练习组数')
    diagnostic_status: str = Field(description='诊断状态: required/in_progress/completed/skipped')


class UserProfileResponse(BaseModel):
    """完整的画像查询响应 data 字段。"""
    profile: Optional[StudentProfileSummary] = Field(None, description='当前画像，尚未完善时为 null')
    created_at: Optional[str] = Field(None, description='创建时间 (ISO 8601)')
    updated_at: Optional[str] = Field(None, description='更新时间 (ISO 8601)')
