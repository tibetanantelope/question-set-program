"""成员二：智能诊断、练习生成相关响应 Schema

字段严格对齐《智学伴接口与并行开发契约》第 8 节。
练习获取接口不得返回 standard_answer；标准答案与解析只在提交后返回。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ==================== 学情诊断 8.1 ====================
class DiagnosisResponse(BaseModel):
    """学情诊断结果"""
    diagnosis_id: int = Field(description='诊断记录ID')
    knowledge_point_id: Optional[int] = Field(None, description='识别出的知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='识别出的知识点名称')
    mastery_score: int = Field(description='当前掌握度: 0-100')
    learning_status: str = Field(description='weak/consolidating/mastered')
    weakness: Optional[str] = Field(None, description='薄弱点分析')
    practice_suggestion: Optional[str] = Field(None, description='建议练习方向')


# ==================== 练习生成 8.2 / 查询 8.3 ====================
class QuestionItem(BaseModel):
    """公共题目结构（不含 standard_answer）"""
    question_id: int = Field(description='题目ID')
    content: str = Field(description='题目内容')
    question_type: str = Field('short_answer', description='题型')
    difficulty: str = Field('easy', description='难度')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')


class PracticeResponse(BaseModel):
    """练习组（生成/查询共用）"""
    practice_id: int = Field(description='练习组ID')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, description='知识点名称')
    difficulty: str = Field(description='难度')
    status: str = Field(description='in_progress/completed')
    questions: List[QuestionItem] = Field(default_factory=list, description='题目列表')


# ==================== 答题分析 8.4 ====================
class AnswerResultItem(BaseModel):
    """单题判题结果（提交后返回，含标准答案与解析）"""
    question_id: int = Field(description='题目ID')
    is_correct: bool = Field(description='是否正确')
    standard_answer: Optional[str] = Field(None, description='标准答案')
    analysis: Optional[str] = Field(None, description='解析')
    error_type: Optional[str] = Field(None, description='knowledge/calculation/reading/method')
    error_description: Optional[str] = Field(None, description='错因说明')
    next_suggestion: Optional[str] = Field(None, description='下一步建议')


class AnswerSubmitResponse(BaseModel):
    """答题提交结果"""
    practice_id: int = Field(description='练习组ID')
    status: str = Field(description='completed')
    question_count: int = Field(description='题目总数')
    correct_count: int = Field(description='答对数量')
    accuracy: float = Field(description='正确率（百分数，保留两位）')
    results: List[AnswerResultItem] = Field(description='逐题分析')
    current_difficulty: Optional[str] = Field(None, description='本组练习难度 easy/medium/hard')
    next_difficulty: Optional[str] = Field(None, description='依据表现给出的下一组建议难度')
