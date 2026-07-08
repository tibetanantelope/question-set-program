"""
In-process short-term memory storage.

This lightweight implementation lets the course project run without an external cache service.
Data is kept per Python process and is cleared
when the backend restarts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
import asyncio


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
    _store: ClassVar[dict[str, list[dict[str, Any]]]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self, max_memory_size: int = 10):
        self.max_memory_size = max_memory_size

    @staticmethod
    def _key(user_id: int, session_id: int) -> str:
        return f"user:{user_id}:session:{session_id}"

    async def add_memory(self, user_id: int, session_id: int, memory: MemoryUnit):
        """Add a memory item, keeping newest records at the head of the list."""
        key = self._key(user_id, session_id)
        async with self._lock:
            memory_list = list(self._store.get(key, []))
            memory_list.insert(0, dict(memory))
            self._store[key] = memory_list[: self.max_memory_size]

    async def get_latest_memories(
        self,
        user_id: int,
        session_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the latest memory items for the user session."""
        key = self._key(user_id, session_id)
        async with self._lock:
            return [dict(item) for item in self._store.get(key, [])[:limit]]

    async def remove_oldest_memory(self, user_id: int, session_id: int) -> dict[str, Any] | None:
        """Remove and return the oldest memory item."""
        key = self._key(user_id, session_id)
        async with self._lock:
            memory_list = self._store.get(key)
            if not memory_list:
                return None
            oldest_memory = memory_list.pop()
            if memory_list:
                self._store[key] = memory_list
            else:
                self._store.pop(key, None)
            return dict(oldest_memory)

    async def clear_all(self, user_id: int, session_id: int):
        """Clear all short-term memories for a user session."""
        key = self._key(user_id, session_id)
        async with self._lock:
            self._store.pop(key, None)

    async def get_memory_size(self, user_id: int, session_id: int) -> int:
        key = self._key(user_id, session_id)
        async with self._lock:
            return len(self._store.get(key, []))

    async def get_max_memory_size(self) -> int:
        return self.max_memory_size

    async def delete_max_memory(self, user_id: int, session_id: int, size: int):
        """Delete the oldest ``size`` memory items."""
        if size <= 0:
            return None

        key = self._key(user_id, session_id)
        async with self._lock:
            memory_list = list(self._store.get(key, []))
            if not memory_list:
                return None

            delete_count = min(size, len(memory_list))
            for _ in range(delete_count):
                memory_list.pop()

            if memory_list:
                self._store[key] = memory_list
            else:
                self._store.pop(key, None)

            return [dict(item) for item in memory_list]


_short_term_memory = ShortTermMemory()


async def get_short_term_memory() -> ShortTermMemory:
    return _short_term_memory


