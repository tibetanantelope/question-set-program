"""Local-development dependency health checks."""

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from backend.agents.memory.vector_store_manager import PERSIST_DIR
from backend.model import AsyncSessionLocal
from backend.schemas.response.base_response import success
from backend.utils.redis_client import get_redis_client

health_router = APIRouter(tags=["system"])


async def _check_mysql() -> str:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    try:
        return "ok" if await get_redis_client().ping() else "error"
    except Exception:
        return "error"


@health_router.get("/health")
async def health_check():
    mysql, redis = await asyncio.gather(_check_mysql(), _check_redis())
    components = {
        "mysql": mysql,
        "redis": redis,
        "chroma": "ok" if Path(PERSIST_DIR).exists() else "not_initialized",
        "llm_config": "ok" if os.getenv("API_KEY") and os.getenv("MODEL_NAME") else "missing",
    }
    status = "ok" if mysql == redis == "ok" else "degraded"
    return success({"status": status, "components": components})
