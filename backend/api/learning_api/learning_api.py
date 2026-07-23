"""成员二：智能诊断与练习生成 API 路由 (/learning)

- POST /learning/diagnose                          学情诊断
- POST /learning/practices                         创建练习组（须带 X-Request-ID）
- GET  /learning/practices/{practice_id}           查询练习组
- POST /learning/practices/{practice_id}/answers   提交答案（须带 X-Request-ID）

user_id 一律从 JWT 获取；练习查询不返回标准答案。
"""

from fastapi import APIRouter, Depends, Header

from backend.api.dependencies import get_current_user
from backend.model.user import User
from backend.schemas.request.learning_request import (
    DiagnosisRequest,
    PracticeGenerateRequest,
    AnswerSubmitRequest,
)
from backend.schemas.response.base_response import success
from backend.services.learning_service.learning_service import (
    LearningService,
    get_learning_service,
)

learning_router = APIRouter(prefix='/learning', tags=['智能诊断与练习'])


@learning_router.post('/diagnose')
async def diagnose(
        req: DiagnosisRequest,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
):
    """学情诊断：识别知识点、评估掌握度、给出薄弱点与练习建议。"""
    data = await service.diagnose(user.id, req)
    return success(data.model_dump())


@learning_router.post('/practices')
async def create_practice(
        req: PracticeGenerateRequest,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """创建针对性练习组（内容校验 + 一次自动重试 + 幂等）。"""
    data = await service.generate_practice(user.id, x_request_id, req)
    return success(data.model_dump(), message='练习生成成功')


@learning_router.get('/practices/{practice_id}')
async def get_practice(
        practice_id: int,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
):
    """查询练习组（仅限本人，不含标准答案）。"""
    data = await service.get_practice(user.id, practice_id)
    return success(data.model_dump())


@learning_router.post('/practices/{practice_id}/answers')
async def submit_answers(
        practice_id: int,
        req: AnswerSubmitRequest,
        user: User = Depends(get_current_user),
        service: LearningService = Depends(get_learning_service),
        x_request_id: str = Header(..., alias='X-Request-ID'),
):
    """提交练习答案：判题、错因分类、难度调整并派发业务事件。"""
    data = await service.submit_answers(user.id, practice_id, x_request_id, req)
    return success(data.model_dump())
