from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserProfileUpdateRequest(BaseModel):
    """保存或更新当前用户画像的请求模型。所有字段均为可选。"""

    stage: Optional[str] = Field(None, description='学段', json_schema_extra={'example': 'junior'})
    grade: Optional[str] = Field(None, description='年级', json_schema_extra={'example': '七年级'})
    subject: Optional[str] = Field(None, description='学科或课程', json_schema_extra={'example': '数学'})
    learning_goal: Optional[str] = Field(None, description='学习目标', json_schema_extra={'example': 'weakness'})
    weekly_study_days: Optional[int] = Field(None, description='每周学习天数: 1-7', json_schema_extra={'example': 5}, ge=1, le=7)
    daily_target_groups: Optional[int] = Field(None, description='每日目标练习组数: 1-5', json_schema_extra={'example': 3}, ge=1, le=5)

    @field_validator('stage')
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('primary', 'junior', 'senior', 'university'):
            raise ValueError('学段必须为 primary/junior/senior/university')
        return v

    @field_validator('learning_goal')
    @classmethod
    def validate_learning_goal(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('daily', 'weakness', 'exam'):
            raise ValueError('学习目标必须为 daily/weakness/exam')
        return v
