"""成员三（第二阶段）：题库管理 Service

职责（对齐《第二阶段五人垂直功能分工》第 5 节）：
- 题目CRUD、审核、上架/下架；
- 管理员操作审计；
- 为练习出题提供已上架题目查询；
- 题目统计更新。
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from backend.core.exceptions import BusinessError
from backend.dao.question_bank_mapper import QuestionBankMapper
from backend.model.learning import Question, KnowledgePoint
from backend.schemas.request.question_bank_request import (
    QuestionCreateRequest,
    QuestionUpdateRequest,
    KnowledgePointCreateRequest,
)
from backend.schemas.response.question_bank_response import (
    QuestionItem,
    QuestionDetail,
    QuestionListResponse,
    KnowledgePointItem,
    KnowledgePointListResponse,
)

_TZ = timezone(timedelta(hours=8))


def _to_item(q: Question) -> QuestionItem:
    correct = q.total_correct or 0
    used = q.usage_count or 0
    rate = round(correct / used * 100, 1) if used > 0 else 0.0
    return QuestionItem(
        question_id=q.id,
        content=q.content[:120] + '...' if len(q.content or '') > 120 else (q.content or ''),
        question_type=q.question_type or 'short_answer',
        difficulty=q.difficulty or 'easy',
        knowledge_point_id=q.knowledge_point_id,
        knowledge_point_name=q.knowledge_point_name,
        subject=q.subject,
        status=q.status or 'approved',
        review_status=q.review_status or 'published',
        source=q.source or 'builtin',
        usage_count=q.usage_count or 0,
        correct_rate=rate,
        created_at=q.created_at.isoformat() if q.created_at else None,
    )


def _to_detail(q: Question) -> QuestionDetail:
    correct = q.total_correct or 0
    used = q.usage_count or 0
    rate = round(correct / used * 100, 1) if used > 0 else 0.0
    return QuestionDetail(
        question_id=q.id,
        content=q.content or '',
        question_type=q.question_type or 'short_answer',
        difficulty=q.difficulty or 'easy',
        knowledge_point_id=q.knowledge_point_id,
        knowledge_point_name=q.knowledge_point_name,
        subject=q.subject,
        status=q.status or 'approved',
        review_status=q.review_status or 'published',
        source=q.source or 'builtin',
        standard_answer=q.standard_answer,
        options=q.options,
        analysis=q.analysis,
        answer_type=q.answer_type or 'short_text',
        usage_count=used,
        total_correct=correct,
        correct_rate=rate,
        created_by=q.created_by,
        reviewed_by=q.reviewed_by,
        reviewed_at=q.reviewed_at.isoformat() if q.reviewed_at else None,
        created_at=q.created_at.isoformat() if q.created_at else None,
    )


class QuestionBankService:
    def __init__(self, mapper: QuestionBankMapper):
        self.mapper = mapper

    # ================== 题目 CRUD ==================

    async def list_questions(
        self,
        *,
        keyword: Optional[str] = None,
        subject: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QuestionListResponse:
        items, total = await self.mapper.list_questions(
            keyword=keyword,
            subject=subject,
            knowledge_point_name=knowledge_point_name,
            difficulty=difficulty,
            status=status,
            review_status=review_status,
            page=page,
            page_size=page_size,
            standalone_only=True,
        )
        pages = math.ceil(total / page_size) if total > 0 else 0
        return QuestionListResponse(
            items=[_to_item(q) for q in items],
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
        )

    async def get_question(self, question_id: int) -> QuestionDetail:
        q = await self.mapper.get_question(question_id)
        if not q:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        return _to_detail(q)

    async def create_question(self, req: QuestionCreateRequest, admin_id: int) -> QuestionDetail:
        q = Question(
            content=req.content,
            question_type=req.question_type,
            difficulty=req.difficulty,
            knowledge_point_id=req.knowledge_point_id,
            knowledge_point_name=req.knowledge_point_name,
            subject=req.subject,
            standard_answer=req.standard_answer,
            options=req.options,
            analysis=req.analysis,
            answer_type=req.answer_type,
            status='pending',
            review_status='off_shelf',
            source='admin',
            created_by=admin_id,
        )
        q = await self.mapper.create_question(q)
        return _to_detail(q)

    async def update_question(self, question_id: int, req: QuestionUpdateRequest) -> QuestionDetail:
        existing = await self.mapper.get_question(question_id)
        if not existing:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        q = await self.mapper.update_question(question_id, updates)
        return _to_detail(q)

    async def delete_question(self, question_id: int) -> None:
        existing = await self.mapper.get_question(question_id)
        if not existing:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        if existing.usage_count > 0:
            raise BusinessError('QUESTION_IN_USE', '该题目已被练习使用，不可删除', 400)
        await self.mapper.delete_question(question_id)

    # ================== 审核与上下架 ==================

    async def approve_question(self, question_id: int, admin_id: int) -> QuestionDetail:
        q = await self.mapper.get_question(question_id)
        if not q:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        if q.status == 'approved':
            raise BusinessError('QUESTION_ALREADY_APPROVED', '题目已审核通过', 409)
        q = await self.mapper.update_question(question_id, {
            'status': 'approved',
            'reviewed_by': admin_id,
            'reviewed_at': datetime.now(_TZ),
        })
        return _to_detail(q)

    async def reject_question(self, question_id: int, admin_id: int) -> QuestionDetail:
        q = await self.mapper.get_question(question_id)
        if not q:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        if q.status == 'rejected':
            raise BusinessError('QUESTION_ALREADY_REJECTED', '题目已被驳回', 409)
        q = await self.mapper.update_question(question_id, {
            'status': 'rejected',
            'reviewed_by': admin_id,
            'reviewed_at': datetime.now(_TZ),
        })
        return _to_detail(q)

    async def publish_question(self, question_id: int) -> QuestionDetail:
        q = await self.mapper.get_question(question_id)
        if not q:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        if q.status != 'approved':
            raise BusinessError('QUESTION_NOT_APPROVED', '只有审核通过的题目才能上架', 400)
        q = await self.mapper.update_question(question_id, {'review_status': 'published'})
        return _to_detail(q)

    async def off_shelf_question(self, question_id: int) -> QuestionDetail:
        q = await self.mapper.get_question(question_id)
        if not q:
            raise BusinessError('QUESTION_NOT_FOUND', '题目不存在', 404)
        q = await self.mapper.update_question(question_id, {'review_status': 'off_shelf'})
        return _to_detail(q)

    # ================== 知识点 ==================

    async def list_knowledge_points(
        self,
        subject: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> KnowledgePointListResponse:
        items, total = await self.mapper.list_knowledge_points(subject, keyword, page, page_size)
        pages = math.ceil(total / page_size) if total > 0 else 0
        return KnowledgePointListResponse(
            items=[KnowledgePointItem(
                id=kp.id, name=kp.name, subject=kp.subject or '数学',
                grade_range=kp.grade_range, parent_id=kp.parent_id,
                description=kp.description,
            ) for kp in items],
            page=page, page_size=page_size, total=total, pages=pages,
        )

    async def create_knowledge_point(self, req: KnowledgePointCreateRequest) -> KnowledgePointItem:
        kp = KnowledgePoint(
            name=req.name, subject=req.subject,
            grade_range=req.grade_range, parent_id=req.parent_id,
            description=req.description,
        )
        kp = await self.mapper.create_knowledge_point(kp)
        return KnowledgePointItem(
            id=kp.id, name=kp.name, subject=kp.subject or '数学',
            grade_range=kp.grade_range, parent_id=kp.parent_id,
            description=kp.description,
        )

    async def get_subjects(self) -> List[str]:
        # 固定返回完整学科列表，避免只有已录入题目学科的情况
        return ['数学', '语文', '英语', '物理', '化学', '生物', '政治', '历史', '地理', '计算机']


# 单例
_question_bank_service: Optional[QuestionBankService] = None


async def get_question_bank_service() -> QuestionBankService:
    global _question_bank_service
    if _question_bank_service is None:
        from backend.dao.question_bank_mapper import get_question_bank_mapper
        mapper = await get_question_bank_mapper()
        _question_bank_service = QuestionBankService(mapper)
    return _question_bank_service
