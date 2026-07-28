from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionItem(BaseModel):
    question_id: int = Field(description='题目编号')
    content: str = Field(description='题目内容')
    question_type: str = Field('short_answer', description='题型')
    difficulty: str = Field('easy', description='难度')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')


class DiagnosticStatusResponse(BaseModel):
    status: str = Field(description='诊断状态: required/in_progress/completed/skipped')
    diagnostic_id: Optional[int] = Field(None, description='进行中的诊断会话ID')


class DiagnosticStartResponse(BaseModel):
    diagnostic_id: int = Field(description='诊断会话ID')
    question_count: int = Field(description='题目数量')
    questions: List[QuestionItem] = Field(description='诊断题目列表')


class MasteryItem(BaseModel):
    knowledge_point_id: int = Field(description='知识点ID')
    knowledge_point_name: str = Field(description='知识点名称')
    mastery_score: int = Field(description='掌握度: 0-100')
    learning_status: str = Field(description='学习状态: weak/consolidating/mastered')


class DiagnosticSubmitResponse(BaseModel):
    status: str = Field(description='completed/skipped')
    masteries: List[MasteryItem] = Field(description='初始化后的知识点掌握度列表')
