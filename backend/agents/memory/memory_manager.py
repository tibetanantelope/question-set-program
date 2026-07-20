"""
后续还可添加功能
将长期记忆存入RAG知识库中：根据用户输入的问题，整合RAG检索和长短期记忆，返回规划器需要的记忆
"""
import asyncio
import json
from typing import Any

from backend.agents.agent.extract_memory_agent import get_extract_memory
from backend.agents.memory.long_term_memory import LongTermMemory
from backend.agents.memory.short_term_memory import ShortTermMemory, MemoryUnit
from backend.agents.memory.vector_store_manager import VectorStoreManager
from backend.core.single_tool import singleMeta
from backend.middleware.logging import get_logger

logger = get_logger(__name__)


class MemoryManager(metaclass=singleMeta):
    def __init__(self,
                 long_term_memory:LongTermMemory,
                 short_term_memory:ShortTermMemory,
                 vector_memory:VectorStoreManager):
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory
        self.vector_memory = vector_memory

    async def get_memory_for_planner(
        self,
        user_id: int,
        session_id: int,
        query_text: str | None = None,
    ) -> dict[str, Any]:
        """Collect short memory, profile and user-filtered semantic memory."""
        tasks = [
            self.short_term_memory.get_latest_memories(user_id, session_id),
            self.long_term_memory.get_by_user_id(user_id),
        ]
        if query_text and query_text.strip():
            tasks.append(self.vector_memory.query(query_text, user_id=user_id, top_k=3))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        short_memory = [] if isinstance(results[0], Exception) else results[0]
        long_memory = None if isinstance(results[1], Exception) else results[1]
        vector_memory = []
        if len(results) == 3 and not isinstance(results[2], Exception):
            vector_memory = results[2]

        for name, result in zip(("short", "long", "vector"), results):
            if isinstance(result, Exception):
                logger.warning("Failed to load %s memory: %s", name, result)

        return {
            "short_memory": short_memory,
            "long_memory": long_memory,
            "vector_memory": vector_memory,
        }

    async def add_memory(self, user_id: int, session_id: int, memory: MemoryUnit):
        """Persist the current turn first, then best-effort archive old memory."""
        try:
            memory_size = await self.short_term_memory.get_memory_size(user_id, session_id)
            max_memory_size = await self.short_term_memory.get_max_memory_size()

            if memory_size < max_memory_size:
                await self.short_term_memory.add_memory(user_id, session_id, memory)
                return

            import time as _time
            all_memories = await self.short_term_memory.get_latest_memories(
                user_id, session_id, memory_size
            )
            memories_to_archive = all_memories[-1:]

            # Redis lpush+ltrim guarantees the current turn is saved even when
            # extraction, embedding or Chroma subsequently fails.
            await self.short_term_memory.add_memory(user_id, session_id, memory)

            try:
                extracted_memory = await get_extract_memory(memories_to_archive)
                for index, memory_dict in enumerate(extracted_memory):
                    text = memory_dict.get('text') or memory_dict.get('memory')
                    if not text:
                        logger.warning("第%s条提炼记忆缺少文本，已跳过", index)
                        continue
                    metadata = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': int(_time.time()),
                        # Chroma metadata only accepts scalar values.
                        'tags': json.dumps(memory_dict.get('tags', []), ensure_ascii=False),
                    }
                    result = await self.vector_memory.add_document(text, metadata)
                    if not result:
                        await asyncio.sleep(0.5)
                        result = await self.vector_memory.add_document(text, metadata)
                    if not result:
                        logger.error("添加第%s条记忆到向量数据库失败", index)
            except Exception:
                logger.exception("归档长期记忆失败，当前短期记忆已正常保存")
        except Exception:
            logger.exception("保存当前短期记忆失败")


    #TODO 完成记忆模块的clear功能


def format_memory_context(memory_data: dict[str, Any]) -> str:
    """Format all memory layers into a bounded, explicit Agent context."""
    sections: list[str] = []

    short_memories = memory_data.get("short_memory") or []
    if short_memories:
        lines = ["【近期对话记录】"]
        for item in reversed(short_memories[:3]):
            memory = item.get("memory", {})
            if memory.get("user_memory"):
                lines.append(f"用户：{memory['user_memory']}")
            if memory.get("model_memory"):
                lines.append(f"助手：{memory['model_memory']}")
        sections.append("\n".join(lines))

    profile = memory_data.get("long_memory")
    if profile:
        if hasattr(profile, "model_dump"):
            profile = profile.model_dump()
        lines = ["【长期学习画像】"]
        for key, label in (
            ("grade", "年级"),
            ("subject", "学科"),
            ("weak_points", "薄弱知识点"),
            ("preferences", "学习偏好"),
        ):
            value = profile.get(key) if isinstance(profile, dict) else None
            if value not in (None, "", {}, []):
                lines.append(f"{label}：{value}")
        if len(lines) > 1:
            sections.append("\n".join(lines))

    vector_memories = memory_data.get("vector_memory") or []
    relevant_lines = [
        f"{index}. {item.get('text', '').strip()}"
        for index, item in enumerate(vector_memories[:3], 1)
        if item.get("text", "").strip()
    ]
    if relevant_lines:
        sections.append("【相关长期记忆】\n" + "\n".join(relevant_lines))

    return "\n\n".join(sections)
