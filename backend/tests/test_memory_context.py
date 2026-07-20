import os

import pytest

os.environ.setdefault(
    "SQL_DATABASE_URL",
    "mysql+asyncmy://test:test@127.0.0.1:3306/test",
)

from backend.agents.memory.memory_manager import MemoryManager, format_memory_context
from backend.agents.memory.short_term_memory import MemoryUnit


class FakeShortMemory:
    async def get_latest_memories(self, user_id, session_id):
        assert (user_id, session_id) == (7, 11)
        return [{
            "memory": {
                "user_memory": "我移项时经常写错符号",
                "model_memory": "建议练习移项变号",
            }
        }]


class FakeLongMemory:
    async def get_by_user_id(self, user_id):
        assert user_id == 7
        return {
            "grade": "七年级",
            "subject": "数学",
            "weak_points": {"移项": 55},
            "preferences": {},
        }


class FakeVectorMemory:
    def __init__(self):
        self.query_args = None

    async def query(self, query_text, user_id=None, top_k=3):
        self.query_args = (query_text, user_id, top_k)
        return [{"text": "用户过去在移项变号处多次出错", "score": 0.91}]


@pytest.mark.asyncio
async def test_planner_memory_queries_vector_store_with_current_user():
    vector = FakeVectorMemory()
    # Bypass the production singleton so the unit test is isolated.
    manager = object.__new__(MemoryManager)
    manager.short_term_memory = FakeShortMemory()
    manager.long_term_memory = FakeLongMemory()
    manager.vector_memory = vector

    result = await manager.get_memory_for_planner(
        user_id=7,
        session_id=11,
        query_text="帮我练习一元一次方程移项",
    )

    assert vector.query_args == ("帮我练习一元一次方程移项", 7, 3)
    assert result["long_memory"]["grade"] == "七年级"
    assert result["vector_memory"][0]["score"] == 0.91


def test_all_memory_layers_are_injected_into_context():
    context = format_memory_context({
        "short_memory": [{
            "memory": {
                "user_memory": "我移项时经常写错符号",
                "model_memory": "建议练习移项变号",
            }
        }],
        "long_memory": {
            "grade": "七年级",
            "subject": "数学",
            "weak_points": {"移项": 55},
            "preferences": {},
        },
        "vector_memory": [{"text": "用户过去在移项变号处多次出错"}],
    })

    assert "【近期对话记录】" in context
    assert "【长期学习画像】" in context
    assert "年级：七年级" in context
    assert "薄弱知识点：{'移项': 55}" in context
    assert "【相关长期记忆】" in context
    assert "用户过去在移项变号处多次出错" in context


@pytest.mark.asyncio
async def test_current_memory_is_saved_when_archive_fails(monkeypatch):
    class FullShortMemory:
        def __init__(self):
            self.saved = []

        async def get_memory_size(self, _user_id, _session_id):
            return 10

        async def get_max_memory_size(self):
            return 10

        async def get_latest_memories(self, _user_id, _session_id, _limit):
            return [{"memory": {"user_memory": "旧记忆", "model_memory": "旧回复"}}]

        async def add_memory(self, user_id, session_id, memory):
            self.saved.append((user_id, session_id, memory))

    async def broken_archive(_memories):
        raise RuntimeError("embedding unavailable")

    short = FullShortMemory()
    manager = object.__new__(MemoryManager)
    manager.short_term_memory = short
    manager.long_term_memory = FakeLongMemory()
    manager.vector_memory = FakeVectorMemory()
    monkeypatch.setattr(
        "backend.agents.memory.memory_manager.get_extract_memory",
        broken_archive,
    )

    current = MemoryUnit("当前问题", "当前回答")
    await manager.add_memory(7, 11, current)

    assert short.saved == [(7, 11, current)]
