from backend.model import engine, Base
from backend.middleware.logging import get_logger
from backend.utils.redis_client import close_redis

logger = get_logger(__name__)


async def startup_event():
    """Create database tables when the application starts."""
    logger.info("Application startup: creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables are ready")


async def shutdown_event():
    """Release database and Redis resources when the application shuts down."""
    logger.info("Application shutdown: releasing resources...")
    await engine.dispose()
    await close_redis()
    logger.info("Database and Redis resources released")