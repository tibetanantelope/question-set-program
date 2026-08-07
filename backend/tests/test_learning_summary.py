"""成员二：用户端学情摘要接口测试

覆盖场景（对齐《五人任务分工》第 4.2 / 4.5 节验收标准）：
- 新用户空数据：摘要结构完整、各计数为 0；
- 掌握度分布固定包含 weak/consolidating/mastered 三桶；
- overall_score 仅统计有答题证据的知识点（新用户为 0）；
- weak_limit 参数校验（越界 422）；
- 未登录访问返回 401。

user_id 一律来自 JWT，接口只聚合“当前登录用户自己”的数据。
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app


# ── Fixtures ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def token(client: AsyncClient) -> str:
    """注册并登录一个全新用户，返回 Bearer token。"""
    username = f"sum_{uuid.uuid4().hex[:8]}"
    password = "test123456"
    await client.post("/login/register", json={"username": username, "password": password})
    resp = await client.post("/login/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 结构与空数据 ──────────────────────────────────────────

class TestLearningSummary:

    @pytest.mark.asyncio
    async def test_summary_structure(self, client: AsyncClient, token: str):
        resp = await client.get("/mastery/summary", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        # 顶层字段齐全
        for key in (
            "overall_score",
            "total_knowledge_points",
            "studied_count",
            "distribution",
            "weakest",
            "pending_corrections",
            "due_reviews",
        ):
            assert key in data

    @pytest.mark.asyncio
    async def test_new_user_empty(self, client: AsyncClient, token: str):
        """全新用户：无掌握度记录，各计数为 0，总体掌握度为 0。"""
        resp = await client.get("/mastery/summary", headers=auth_headers(token))
        data = resp.json()["data"]
        assert data["overall_score"] == 0
        assert data["total_knowledge_points"] == 0
        assert data["studied_count"] == 0
        assert data["pending_corrections"] == 0
        assert data["due_reviews"] == 0
        assert data["weakest"] == []

    @pytest.mark.asyncio
    async def test_distribution_three_buckets(self, client: AsyncClient, token: str):
        """掌握度分布固定返回 weak/consolidating/mastered 三桶，口径与运营看板一致。"""
        resp = await client.get("/mastery/summary", headers=auth_headers(token))
        dist = resp.json()["data"]["distribution"]
        assert [d["status"] for d in dist] == ["weak", "consolidating", "mastered"]
        assert all(d["count"] == 0 for d in dist)
        assert all("label" in d for d in dist)

    @pytest.mark.asyncio
    async def test_weak_limit_param(self, client: AsyncClient, token: str):
        """weak_limit 合法值可正常请求。"""
        resp = await client.get(
            "/mastery/summary?weak_limit=3", headers=auth_headers(token)
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_weak_limit_out_of_range(self, client: AsyncClient, token: str):
        """weak_limit 越界返回 422。"""
        resp = await client.get(
            "/mastery/summary?weak_limit=0", headers=auth_headers(token)
        )
        assert resp.status_code == 422
        resp = await client.get(
            "/mastery/summary?weak_limit=999", headers=auth_headers(token)
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient):
        """未登录访问返回 401。"""
        resp = await client.get("/mastery/summary")
        assert resp.status_code == 401
