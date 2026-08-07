"""成员二（第二阶段）：管理员运营看板接口测试

覆盖场景（对齐《第二阶段五人垂直功能分工》第 4.5 节 + 契约第 17 节）：
- 正常成功流程（overview / subjects / trend）
- 未登录访问 401
- 权限不足访问 403（普通用户）
- 参数校验失败 422（days 越界）
- 空数据与聚合结构完整性
- 趋势按天补零，points 数量等于 days
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/login/login", json={"username": "admin01", "password": "admin123456"}
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    username = f"dash_{uuid.uuid4().hex[:8]}"
    await client.post("/login/register", json={"username": username, "password": "test123456"})
    resp = await client.post("/login/login", json={"username": username, "password": "test123456"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestDashboardOverview:
    async def test_overview_success(self, client: AsyncClient, admin_token: str):
        resp = await client.get("/admin/dashboard/overview", headers=_auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        data = body["data"]
        # 结构完整性：四组统计都在
        assert set(data["user_stats"]) == {"total_users", "active_users", "new_users"}
        assert set(data["practice_stats"]) == {
            "practice_total", "practice_completed", "completion_rate", "avg_accuracy",
        }
        assert set(data["mistake_stats"]) == {
            "mistake_total", "review_total", "review_completed", "review_completion_rate",
        }
        # 掌握度分布固定三档
        statuses = [d["status"] for d in data["mastery_distribution"]]
        assert statuses == ["weak", "consolidating", "mastered"]

    async def test_overview_days_param(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            "/admin/dashboard/overview", params={"days": 30}, headers=_auth(admin_token)
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["days"] == 30

    async def test_overview_days_out_of_range(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            "/admin/dashboard/overview", params={"days": 999}, headers=_auth(admin_token)
        )
        assert resp.status_code == 422

    async def test_overview_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/admin/dashboard/overview")
        assert resp.status_code == 401

    async def test_overview_forbidden_for_user(self, client: AsyncClient, user_token: str):
        resp = await client.get("/admin/dashboard/overview", headers=_auth(user_token))
        assert resp.status_code == 403


class TestDashboardSubjects:
    async def test_subjects_success(self, client: AsyncClient, admin_token: str):
        resp = await client.get("/admin/dashboard/subjects", headers=_auth(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        assert isinstance(body["data"]["items"], list)

    async def test_subjects_forbidden_for_user(self, client: AsyncClient, user_token: str):
        resp = await client.get("/admin/dashboard/subjects", headers=_auth(user_token))
        assert resp.status_code == 403


class TestDashboardTrend:
    async def test_trend_zero_filled(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            "/admin/dashboard/trend", params={"days": 7}, headers=_auth(admin_token)
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["days"] == 7
        # 缺失日期补零 → points 恰好 7 个，且按日期升序
        assert len(data["points"]) == 7
        dates = [p["date"] for p in data["points"]]
        assert dates == sorted(dates)
        for p in data["points"]:
            assert p["record_count"] >= 0
            assert p["active_users"] >= 0

    async def test_trend_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/admin/dashboard/trend")
        assert resp.status_code == 401

    async def test_trend_forbidden_for_user(self, client: AsyncClient, user_token: str):
        resp = await client.get("/admin/dashboard/trend", headers=_auth(user_token))
        assert resp.status_code == 403
