from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
import jwt

from backend.core.security import SECRET_KEY, ALGORITHM
from backend.model import get_db
from backend.model.user import User
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/login", auto_error=False)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无效的凭证或 Token 已过期",
    headers={"WWW-Authenticate": "Bearer"},
)

forbidden_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="无权访问此资源",
)

disabled_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="账号已被禁用，请联系管理员",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前登录用户。token 缺失或无效返回 401。"""
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """获取当前用户并检查是否被禁用。"""
    if not user.is_active:
        raise disabled_exception
    return user


async def get_current_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    """获取当前管理员用户。普通用户返回 403。"""
    if not user.is_admin:
        raise forbidden_exception
    return user


async def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
