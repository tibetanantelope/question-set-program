"""管理员 API：题库管理 (/admin/questions)

- GET    /admin/questions                题目列表（搜索+筛选+分页）
- GET    /admin/questions/{id}            题目详情
- POST   /admin/questions                新增题目
- PUT    /admin/questions/{id}            编辑题目
- DELETE /admin/questions/{id}            删除题目
- POST   /admin/questions/{id}/approve    审核通过
- POST   /admin/questions/{id}/reject     审核驳回
- POST   /admin/questions/{id}/publish    上架
- POST   /admin/questions/{id}/off-shelf  下架

- GET    /admin/knowledge-points          知识点列表
- POST   /admin/knowledge-points          新增知识点
- GET    /admin/subjects                  学科列表

普通用户访问返回 403。
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.dependencies import get_current_admin, get_client_ip
from backend.model.user import User
from backend.schemas.request.question_bank_request import (
    QuestionCreateRequest,
    QuestionUpdateRequest,
    KnowledgePointCreateRequest,
)
from backend.schemas.response.base_response import success
from backend.schemas.response.question_bank_response import QuestionDetail
from backend.services.admin_service.admin_service import admin_service
from backend.services.question_bank_service import (
    QuestionBankService,
    get_question_bank_service,
)

admin_question_router = APIRouter(tags=['管理员-题库管理'])


@admin_question_router.get('/admin/questions')
async def list_questions(
    keyword: str | None = Query(None, description='搜索题目内容'),
    subject: str | None = Query(None, description='学科筛选'),
    knowledge_point_name: str | None = Query(None, description='知识点筛选'),
    difficulty: str | None = Query(None, description='难度: easy/medium/hard'),
    status: str | None = Query(None, description='审核状态: draft/pending/approved/rejected'),
    review_status: str | None = Query(None, description='上架状态: published/off_shelf'),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.list_questions(
        keyword=keyword, subject=subject,
        knowledge_point_name=knowledge_point_name,
        difficulty=difficulty, status=status,
        review_status=review_status,
        page=page, page_size=page_size,
    )
    return success(data.model_dump())


@admin_question_router.get('/admin/questions/{question_id}')
async def get_question(
    question_id: int,
    admin: User = Depends(get_current_admin),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.get_question(question_id)
    return success(data.model_dump())


@admin_question_router.post('/admin/questions')
async def create_question(
    req: QuestionCreateRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.create_question(req, admin.id)
    await admin_service.record_audit(admin, 'create_question', 'question', data.question_id, ip)
    return success(data.model_dump(), message='题目已创建')


@admin_question_router.put('/admin/questions/{question_id}')
async def update_question(
    question_id: int,
    req: QuestionUpdateRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.update_question(question_id, req)
    await admin_service.record_audit(admin, 'update_question', 'question', question_id, ip)
    return success(data.model_dump(), message='题目已更新')


@admin_question_router.delete('/admin/questions/{question_id}')
async def delete_question(
    question_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    await service.delete_question(question_id)
    await admin_service.record_audit(admin, 'delete_question', 'question', question_id, ip)
    return success(None, message='题目已删除')


@admin_question_router.post('/admin/questions/{question_id}/approve')
async def approve_question(
    question_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.approve_question(question_id, admin.id)
    await admin_service.record_audit(admin, 'approve_question', 'question', question_id, ip)
    return success(data.model_dump(), message='审核已通过')


@admin_question_router.post('/admin/questions/{question_id}/reject')
async def reject_question(
    question_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.reject_question(question_id, admin.id)
    await admin_service.record_audit(admin, 'reject_question', 'question', question_id, ip)
    return success(data.model_dump(), message='审核已驳回')


@admin_question_router.post('/admin/questions/{question_id}/publish')
async def publish_question(
    question_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.publish_question(question_id)
    await admin_service.record_audit(admin, 'publish_question', 'question', question_id, ip)
    return success(data.model_dump(), message='题目已上架')


@admin_question_router.post('/admin/questions/{question_id}/off-shelf')
async def off_shelf_question(
    question_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    ip: str = Depends(get_client_ip),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.off_shelf_question(question_id)
    await admin_service.record_audit(admin, 'off_shelf_question', 'question', question_id, ip)
    return success(data.model_dump(), message='题目已下架')


# ================== 知识点 ==================

@admin_question_router.get('/admin/knowledge-points')
async def list_knowledge_points(
    subject: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.list_knowledge_points(subject=subject, keyword=keyword, page=page, page_size=page_size)
    return success(data.model_dump())


@admin_question_router.post('/admin/knowledge-points')
async def create_knowledge_point(
    req: KnowledgePointCreateRequest,
    admin: User = Depends(get_current_admin),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.create_knowledge_point(req)
    return success(data.model_dump(), message='知识点已创建')


@admin_question_router.get('/admin/subjects')
async def list_subjects(
    admin: User = Depends(get_current_admin),
    service: QuestionBankService = Depends(get_question_bank_service),
):
    data = await service.get_subjects()
    return success(data)
