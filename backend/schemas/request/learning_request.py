"""成员二：智能诊断、练习生成相关请求 Schema

字段严格对齐《智学伴接口与并行开发契约》第 8 节，冻结不可随意更改。
"""

from typing import List

from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    """学情诊断请求 POST /learning/diagnose"""
    session_id: int | None = Field(None, description='关联学习会话ID（可选）')
    input_type: str = Field(..., description='question/learning_question/weakness')
    content: str = Field(..., min_length=1, max_length=2000, description='题目、问题或薄弱点描述')


class PracticeGenerateRequest(BaseModel):
    """创建练习组请求 POST /learning/practices（请求头须含 X-Request-ID）"""
    diagnosis_id: int | None = Field(None, description='关联诊断ID（可选）')
    question_count: int = Field(3, ge=3, le=5, description='题目数量，只能为 3~5')
    difficulty: str | None = Field(None, description='指定难度 easy/medium/hard（可选，用于"再练一组"沿用调整后的难度）')


class AnswerItem(BaseModel):
    """单题答案"""
    question_id: int = Field(..., description='题目ID')
    answer: str = Field(..., description='学生答案')


class AnswerSubmitRequest(BaseModel):
    """提交练习答案请求 POST /learning/practices/{practice_id}/answers"""
    answers: List[AnswerItem] = Field(..., description='答案列表', min_length=1)
