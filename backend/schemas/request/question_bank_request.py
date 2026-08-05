"""成员三（第二阶段）：题库管理请求 Schema"""

from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionCreateRequest(BaseModel):
    """新增题目"""
    content: str = Field(..., min_length=1, max_length=4000, description='题目内容')
    question_type: str = Field('short_answer', description='choice/short_answer/fill_blank/true_false')
    difficulty: str = Field('easy', description='easy/medium/hard')
    knowledge_point_id: Optional[int] = Field(None, description='知识点ID')
    knowledge_point_name: Optional[str] = Field(None, max_length=128, description='知识点名称')
    subject: Optional[str] = Field(None, max_length=32, description='学科')
    standard_answer: Optional[str] = Field(None, max_length=4000, description='标准答案')
    options: Optional[list] = Field(None, description='选择题选项 [{label, content, is_correct}]')
    analysis: Optional[str] = Field(None, max_length=4000, description='解析')
    answer_type: str = Field('short_text', description='答案类型')


class QuestionUpdateRequest(BaseModel):
    """编辑题目（所有字段可选）"""
    content: Optional[str] = Field(None, min_length=1, max_length=4000)
    question_type: Optional[str] = Field(None)
    difficulty: Optional[str] = Field(None)
    knowledge_point_id: Optional[int] = Field(None)
    knowledge_point_name: Optional[str] = Field(None, max_length=128)
    subject: Optional[str] = Field(None, max_length=32)
    standard_answer: Optional[str] = Field(None, max_length=4000)
    options: Optional[list] = Field(None)
    analysis: Optional[str] = Field(None, max_length=4000)
    answer_type: Optional[str] = Field(None)


class QuestionReviewRequest(BaseModel):
    """审核操作"""
    pass  # 只需管理员身份 + question_id


class KnowledgePointCreateRequest(BaseModel):
    """新增知识点"""
    name: str = Field(..., min_length=1, max_length=128)
    subject: str = Field('数学', max_length=32)
    grade_range: Optional[str] = Field(None, max_length=64)
    parent_id: Optional[int] = Field(None)
    description: Optional[str] = Field(None, max_length=1000)
