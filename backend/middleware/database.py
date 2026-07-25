"""数据库中间件：提供统一的会话管理和依赖注入。

使用方式：
- 直接获取会话：`async with get_session() as session:`
- FastAPI 依赖注入：`db: AsyncSession = Depends(get_db)`
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.model import AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取一个异步数据库会话（上下文管理器）。"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取异步数据库会话。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
