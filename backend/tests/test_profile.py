"""成员一：画像、诊断、会话记忆 接口测试"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.model import AsyncSessionLocal, Base
from backend.schemas.request.user_profile_update_request import UserProfileUpdateRequest


# ── Fixtures ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def token(client: AsyncClient) -> str:
    """注册并登录测试用户，返回 Bearer token。"""
    import uuid
    username = f"test_{uuid.uuid4().hex[:8]}"
    password = "test123456"

    await client.post("/login/register", json={"username": username, "password": password})
    resp = await client.post("/login/login", json={"username": username, "password": password})
    data = resp.json()
    return data["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def profile_with_token(client: AsyncClient, token: str):
    """创建一个已保存画像的测试用户，返回 (token, profile_data)。"""
    h = auth_headers(token)
    payload = {
        "stage": "junior",
        "grade": "七年级",
        "subject": "数学",
        "learning_goal": "weakness",
        "weekly_study_days": 5,
        "daily_target_groups": 3,
    }
    await client.put("/profile/me", headers=h, json=payload)
    return token, payload


# ── 画像接口测试 ──────────────────────────────────────────

class TestProfileApi:
    """GET /profile/me 和 PUT /profile/me"""

    async def test_get_empty_profile_returns_null(self, client: AsyncClient, token: str):
        """尚未完善画像时 data.profile 为 null，HTTP 仍为 200。"""
        resp = await client.get("/profile/me", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        assert body["data"]["profile"] is None

    async def test_save_and_read_profile(self, client: AsyncClient, token: str):
        """保存后能正确读取。"""
        h = auth_headers(token)
        payload = {
            "stage": "junior",
            "grade": "七年级",
            "subject": "数学",
            "learning_goal": "weakness",
            "weekly_study_days": 5,
            "daily_target_groups": 3,
        }

        put_resp = await client.put("/profile/me", headers=h, json=payload)
        assert put_resp.status_code == 200
        data = put_resp.json()["data"]
        assert data["stage"] == "junior"
        assert data["diagnostic_status"] == "required"

        get_resp = await client.get("/profile/me", headers=h)
        assert get_resp.status_code == 200
        profile = get_resp.json()["data"]["profile"]
        assert profile is not None
        assert profile["stage"] == "junior"
        assert profile["grade"] == "七年级"

    async def test_partial_update_keeps_old_fields(self, client: AsyncClient, profile_with_token):
        """部分更新只改变提交的字段。"""
        token, _ = profile_with_token
        h = auth_headers(token)

        await client.put("/profile/me", headers=h, json={"weekly_study_days": 7})
        resp = await client.get("/profile/me", headers=h)
        profile = resp.json()["data"]["profile"]
        assert profile["weekly_study_days"] == 7
        assert profile["stage"] == "junior"  # 不受影响

    async def test_cannot_access_other_user(self, client: AsyncClient, token: str):
        """验证接口不允许用户间数据交叉。GET /profile/me 不接收 user_id。"""
        h = auth_headers(token)
        # 先保存自己的画像
        await client.put("/profile/me", headers=h, json={
            "stage": "junior", "grade": "七年级", "subject": "数学", "learning_goal": "daily"
        })
        resp = await client.get("/profile/me", headers=h)
        assert resp.json()["data"]["profile"]["grade"] == "七年级"

    async def test_invalid_stage_rejected(self, client: AsyncClient, token: str):
        """学段不在枚举范围内返回 422。"""
        resp = await client.put("/profile/me", headers=auth_headers(token), json={"stage": "invalid"})
        assert resp.status_code == 422

    async def test_invalid_learning_goal_rejected(self, client: AsyncClient, token: str):
        resp = await client.put("/profile/me", headers=auth_headers(token), json={"learning_goal": "bad"})
        assert resp.status_code == 422

    async def test_weekly_days_out_of_range(self, client: AsyncClient, token: str):
        resp = await client.put("/profile/me", headers=auth_headers(token), json={"weekly_study_days": 8})
        assert resp.status_code == 422

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/profile/me")
        assert resp.status_code == 401


# ── 诊断接口测试 ──────────────────────────────────────────

class TestDiagnosticApi:

    async def test_status_required_by_default(self, client: AsyncClient, profile_with_token):
        token, _ = profile_with_token
        resp = await client.get("/profile/diagnostic/status", headers=auth_headers(token))
        assert resp.json()["data"]["status"] == "required"

    async def test_start_diagnostic(self, client: AsyncClient, profile_with_token):
        token, _ = profile_with_token
        resp = await client.post("/profile/diagnostic/start", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["diagnostic_id"] > 0
        assert len(data["questions"]) == 5
        for q in data["questions"]:
            assert "question_id" in q
            assert q["content"]
            assert q["difficulty"] in ("easy", "medium", "hard")

    async def test_submit_diagnostic(self, client: AsyncClient, profile_with_token):
        token, _ = profile_with_token
        h = auth_headers(token)

        start = await client.post("/profile/diagnostic/start", headers=h)
        diag_id = start.json()["data"]["diagnostic_id"]
        questions = start.json()["data"]["questions"]

        answers = [{"question_id": q["question_id"], "answer": "test"} for q in questions]
        resp = await client.post("/profile/diagnostic/submit", headers=h, json={
            "diagnostic_id": diag_id, "answers": answers
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert len(data["masteries"]) > 0
        for m in data["masteries"]:
            assert 0 <= m["mastery_score"] <= 100
            assert m["learning_status"] in ("weak", "consolidating", "mastered")

    async def test_skip_diagnostic(self, client: AsyncClient, profile_with_token):
        token, _ = profile_with_token
        h = auth_headers(token)

        resp = await client.post("/profile/diagnostic/skip", headers=h)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "skipped"
        assert resp.json()["data"]["masteries"] == []

        # 确认状态已更新
        status = await client.get("/profile/diagnostic/status", headers=h)
        assert status.json()["data"]["status"] == "skipped"

    async def test_duplicate_submit_rejected(self, client: AsyncClient, profile_with_token):
        token, _ = profile_with_token
        h = auth_headers(token)

        start = await client.post("/profile/diagnostic/start", headers=h)
        diag_id = start.json()["data"]["diagnostic_id"]
        questions = start.json()["data"]["questions"]
        answers = [{"question_id": q["question_id"], "answer": "x"} for q in questions]

        # 第一次提交
        await client.post("/profile/diagnostic/submit", headers=h, json={
            "diagnostic_id": diag_id, "answers": answers
        })
        # 重复提交
        resp = await client.post("/profile/diagnostic/submit", headers=h, json={
            "diagnostic_id": diag_id, "answers": answers
        })
        assert resp.status_code == 409

    async def test_diagnostic_requires_profile(self, client: AsyncClient, token: str):
        """未完善画像时发起诊断返回 400。"""
        resp = await client.post("/profile/diagnostic/start", headers=auth_headers(token))
        assert resp.status_code == 400

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/profile/diagnostic/status")
        assert resp.status_code == 401


# ── 会话记忆测试 ──────────────────────────────────────────

class TestSessionMemory:
    async def test_clear_session_memory(self, client: AsyncClient, token: str):
        h = auth_headers(token)
        resp = await client.delete("/sessions/1/memory", headers=h)
        assert resp.status_code == 200
        assert resp.json()["code"] == "OK"

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/sessions/1/memory")
        assert resp.status_code == 401


# ── Service 层测试 ────────────────────────────────────────

class TestProfileService:
    async def test_get_summary_raises_when_not_completed(self):
        from backend.services.profile_service.profile_service import ProfileService
        from backend.dao.user_profile_mapper import UserProfileMapper
        from backend.model import AsyncSessionLocal
        import pytest
        from backend.core.exceptions import BusinessError

        svc = ProfileService(mapper=UserProfileMapper(AsyncSessionLocal))
        with pytest.raises(BusinessError) as exc:
            await svc.get_summary(999999)
        assert exc.value.code == "PROFILE_NOT_COMPLETED"

    async def test_save_and_get_summary(self, client: AsyncClient, token: str):
        from backend.services.profile_service.profile_service import ProfileService
        from backend.dao.user_profile_mapper import UserProfileMapper
        from backend.model import AsyncSessionLocal

        # 先用 API 保存画像（以便有真实 user_id）
        import jwt
        from backend.core.security import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["user_id"]

        # 先通过 API 确保画像存在
        h = auth_headers(token)
        await client.put("/profile/me", headers=h, json={
            "stage": "junior", "grade": "七年级", "subject": "数学", "learning_goal": "exam"
        })

        svc = ProfileService(mapper=UserProfileMapper(AsyncSessionLocal))
        summary = await svc.get_summary(user_id)
        assert summary.stage == "junior"
        assert summary.grade == "七年级"
        assert 1 <= summary.weekly_study_days <= 7
        assert 1 <= summary.daily_target_groups <= 5
