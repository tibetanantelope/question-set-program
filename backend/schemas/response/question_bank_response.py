"""成员三（第二阶段）：题库管理响应 Schema"""

from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionItem(BaseModel):
    """题目列表项"""
    question_id: int
    content: str
    question_type: str = 'short_answer'
    difficulty: str = 'easy'
    knowledge_point_id: Optional[int] = None
    knowledge_point_name: Optional[str] = None
    subject: Optional[str] = None
    status: str = 'approved'
    review_status: str = 'published'
    source: str = 'builtin'
    usage_count: int = 0
    correct_rate: float = 0.0
    created_at: Optional[str] = None


class QuestionDetail(BaseModel):
    """题目详情"""
    question_id: int
    content: str
    question_type: str
    difficulty: str
    knowledge_point_id: Optional[int] = None
    knowledge_point_name: Optional[str] = None
    subject: Optional[str] = None
    status: str
    review_status: str
    source: str
    standard_answer: Optional[str] = None
    options: Optional[list] = None
    analysis: Optional[str] = None
    answer_type: str = 'short_text'
    usage_count: int = 0
    total_correct: int = 0
    correct_rate: float = 0.0
    created_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None


class QuestionListResponse(BaseModel):
    """分页题目列表"""
    items: List[QuestionItem] = []
    page: int = 1
    page_size: int = 20
    total: int = 0
    pages: int = 0


class KnowledgePointItem(BaseModel):
    """知识点列表项"""
    id: int
    name: str
    subject: str = '数学'
    grade_range: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None


class KnowledgePointListResponse(BaseModel):
    """分页知识点列表"""
    items: List[KnowledgePointItem] = []
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0
