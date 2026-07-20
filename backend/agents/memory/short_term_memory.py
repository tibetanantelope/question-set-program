"""Redis-backed short-term memory storage."""
from __future__ import annotations

from datetime import datetime
from typing import Any
import json

from backend.utils.redis_client import get_redis_client


class MemoryUnit(dict):
    def __init__(self, user_memory: str = "", model_memory: str = ""):
        super().__init__(
            memory={
                "user_memory": user_memory,
                "model_memory": model_memory,
            },
            timestamp=datetime.now().isoformat(),
        )


class ShortTermMemory:
    def __init__(self, max_memory_size: int = 10):
        self.max_memory_size = max_memory_size
        self.redis = get_redis_client()

    @staticmethod
    def _key(user_id: int, session_id: int) -> str:
        return f"user:{user_id}:session:{session_id}:short_term_memory"

    @staticmethod
    def _deserialize(raw_memory: str | bytes | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw_memory, dict):
            return raw_memory
        if isinstance(raw_memory, bytes):
            raw_memory = raw_memory.decode("utf-8")
        return json.loads(raw_memory)

    async def add_memory(self, user_id: int, session_id: int, memory: MemoryUnit):
        """Add a memory item, keeping newest records at the head of the Redis list."""
        key = self._key(user_id, session_id)
        await self.redis.lpush(key, json.dumps(dict(memory), ensure_ascii=False))
        await self.redis.ltrim(key, 0, self.max_memory_size - 1)

    async def get_latest_memories(
        self,
        user_id: int,
        session_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the latest memory items for the user session."""
        key = self._key(user_id, session_id)
        raw_memories = await self.redis.lrange(key, 0, limit - 1)
        return [self._deserialize(item) for item in raw_memories]

    async def remove_oldest_memory(self, user_id: int, session_id: int) -> dict[str, Any] | None:
        """Remove and return the oldest memory item."""
        key = self._key(user_id, session_id)
        raw_memory = await self.redis.rpop(key)
        if raw_memory is None:
            return None
        return self._deserialize(raw_memory)

    async def clear_all(self, user_id: int, session_id: int):
        """Clear all short-term memories for a user session."""
        key = self._key(user_id, session_id)
        await self.redis.delete(key)

    async def get_memory_size(self, user_id: int, session_id: int) -> int:
        key = self._key(user_id, session_id)
        return await self.redis.llen(key)

    async def get_max_memory_size(self) -> int:
        return self.max_memory_size

    async def delete_max_memory(self, user_id: int, session_id: int, size: int):
        """Delete the oldest ``size`` memory items and return the remaining memories."""
        if size <= 0:
            return None

        key = self._key(user_id, session_id)
        memory_size = await self.redis.llen(key)
        if memory_size == 0:
            return None

        delete_count = min(size, memory_size)
        for _ in range(delete_count):
            await self.redis.rpop(key)

        raw_memories = await self.redis.lrange(key, 0, -1)
        return [self._deserialize(item) for item in raw_memories]


_short_term_memory = ShortTermMemory()


async def get_short_term_memory() -> ShortTermMemory:
    return _short_term_memory
