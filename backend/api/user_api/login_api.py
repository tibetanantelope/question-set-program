from fastapi import APIRouter, Request, Depends

from backend.api.dependencies import get_current_active_user, get_client_ip
from backend.model.user import User
from backend.schemas.response.base_response import success
from backend.services.login_service.login_service import login_service

login_router = APIRouter(prefix='/login', tags=['login'])

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=6, max_length=20, description='用户名')
    password: str = Field(min_length=6, max_length=20, description='用户密码')


@login_router.post('/login')
async def login_user(request: Request, req: LoginRequest):
    """用户/管理员登录。"""
    ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    result = await login_service.login(req.username, req.password, ip)
    return result


@login_router.post('/register')
async def register_user(req: LoginRequest):
    """用户注册。"""
    data = await login_service.register(req.username, req.password)
    return data


@login_router.get('/me')
async def get_me(user: User = Depends(get_current_active_user)):
    """查询当前登录用户信息。"""
    return success(await login_service.get_my_info(user.id))
