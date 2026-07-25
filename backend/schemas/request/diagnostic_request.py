from typing import List

from pydantic import BaseModel, Field


class DiagnosticAnswerItem(BaseModel):
    question_id: int = Field(..., description='题目编号')
    answer: str = Field(..., description='学生答案', min_length=1)


class DiagnosticSubmitRequest(BaseModel):
    diagnostic_id: int = Field(..., description='诊断会话ID', gt=0)
    answers: List[DiagnosticAnswerItem] = Field(..., description='答案列表', min_length=1)
