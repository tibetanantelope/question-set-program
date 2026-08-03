import os

from backend.model import engine, Base
from backend.middleware.logging import get_logger
from backend.utils.redis_client import close_redis

logger = get_logger(__name__)


async def _ensure_admin_account():
    """确保至少存在一个管理员账号。"""
    from sqlalchemy import select, text
    from backend.model.user import User
    from backend.core.security import get_password_hash, DEMO_ADMIN_USERNAME, DEMO_ADMIN_PASSWORD

    async with engine.begin() as conn:
        result = await conn.execute(
            select(User).where(User.role == 'admin')
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            hashed = get_password_hash(DEMO_ADMIN_PASSWORD)
            await conn.execute(
                text(
                    "INSERT INTO user (username, password, role, status) "
                    "VALUES (:username, :password, :role, :status)"
                ),
                {"username": DEMO_ADMIN_USERNAME, "password": hashed, "role": "admin", "status": "active"},
            )
            logger.info(
                "Demo admin account created: username=%s", DEMO_ADMIN_USERNAME
            )


async def startup_event():
    logger.info("Application startup: creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables are ready")

    await _ensure_admin_account()


async def shutdown_event():
    logger.info("Application shutdown: releasing resources...")
    await engine.dispose()
    await close_redis()
    logger.info("Database and Redis resources released")
