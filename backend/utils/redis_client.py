"""Async Redis client shared by backend services."""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv("backend/.env")
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """Return a singleton async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the shared Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
