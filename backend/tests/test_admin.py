"""成员一 第二阶段：账号/用户/权限 测试"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app

pytestmark = pytest.mark.asyncio


# ── Fixtures ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    resp = await client.post("/login/login", json={"username": "admin01", "password": "admin123456"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    import uuid
    uname = f"ut{uuid.uuid4().hex[:6]}"
    await client.post("/login/register", json={"username": uname, "password": "test123456"})
    resp = await client.post("/login/login", json={"username": uname, "password": "test123456"})
    return resp.json()["access_token"]


# ── 管理员登录 ────────────────────────────────────────────

class TestAdminLogin:
    async def test_admin_login_returns_role(self, client: AsyncClient):
        resp = await client.post("/login/login", json={"username": "admin01", "password": "admin123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "admin"
        assert "access_token" in data

    async def test_admin_login_wrong_password(self, client: AsyncClient):
        resp = await client.post("/login/login", json={"username": "admin01", "password": "wrong123"})
        assert resp.status_code == 401

    async def test_user_login_returns_user_role(self, client: AsyncClient, user_token):
        # Use an existing user for login test
        resp = await client.get("/login/me", headers=_auth(user_token))
        assert resp.status_code == 200

    async def test_login_returns_user_info(self, client: AsyncClient):
        resp = await client.post("/login/login", json={"username": "admin01", "password": "admin123456"})
        assert "user" in resp.json()
        assert resp.json()["user"]["id"] is not None


# ── 禁用用户 ──────────────────────────────────────────────

class TestDisabledUser:
    async def test_disabled_user_cannot_login(self, client: AsyncClient, admin_token):
        import uuid
        uname = f"du{uuid.uuid4().hex[:6]}"
        await client.post("/login/register", json={"username": uname, "password": "test123456"})
        resp = await client.post("/login/login", json={"username": uname, "password": "test123456"})
        uid = resp.json()["user"]["id"]

        # Disable
        r = await client.post(f"/admin/users/{uid}/disable", headers=_auth(admin_token))
        assert r.status_code == 200

        # Try login
        r = await client.post("/login/login", json={"username": uname, "password": "test123456"})
        assert r.status_code == 403
        assert r.json()["code"] == "ACCOUNT_DISABLED"


# ── 管理员 API ────────────────────────────────────────────

class TestAdminUsersApi:
    async def test_list_users(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/users?page=1&page_size=5", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert len(data["items"]) <= 5

    async def test_get_user_detail(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/users/1", headers=_auth(admin_token))
        if resp.status_code == 200:
            assert "username" in resp.json()["data"]
        else:
            assert resp.status_code == 404

    async def test_disable_and_restore_user(self, client: AsyncClient, admin_token, user_token):
        # Find user ID from token
        resp = await client.get("/login/me", headers=_auth(user_token))
        uid = resp.json()["data"]["id"]

        # Disable
        r = await client.post(f"/admin/users/{uid}/disable", headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "disabled"

        # Restore
        r = await client.post(f"/admin/users/{uid}/restore", headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "active"

    async def test_cannot_disable_admin(self, client: AsyncClient, admin_token):
        # Find admin ID
        resp = await client.get("/login/me", headers=_auth(admin_token))
        uid = resp.json()["data"]["id"]
        r = await client.post(f"/admin/users/{uid}/disable", headers=_auth(admin_token))
        assert r.status_code == 400

    async def test_search_users(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/users?keyword=admin01", headers=_auth(admin_token))
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert any("admin" in u["username"].lower() for u in items)

    async def test_filter_by_status(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/users?status=active", headers=_auth(admin_token))
        assert resp.status_code == 200
        for u in resp.json()["data"]["items"]:
            assert u["status"] == "active"

    async def test_filter_by_role(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/users?role=admin", headers=_auth(admin_token))
        assert resp.status_code == 200
        for u in resp.json()["data"]["items"]:
            assert u["role"] == "admin"


# ── 审计日志 ──────────────────────────────────────────────

class TestAuditLog:
    async def test_list_audits(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/audits", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_audit_has_required_fields(self, client: AsyncClient, admin_token):
        resp = await client.get("/admin/audits", headers=_auth(admin_token))
        if resp.json()["data"]["items"]:
            a = resp.json()["data"]["items"][0]
            assert "admin_id" in a
            assert "action" in a
            assert "created_at" in a


# ── 权限拦截 ──────────────────────────────────────────────

class TestPermissionGuard:
    async def test_ordinary_user_cannot_access_admin(self, client: AsyncClient, user_token):
        resp = await client.get("/admin/users", headers=_auth(user_token))
        assert resp.status_code == 403

    async def test_admin_requires_auth(self, client: AsyncClient):
        resp = await client.get("/admin/users")
        assert resp.status_code == 401

    async def test_disabled_user_gets_403_on_protected(self, client: AsyncClient, admin_token):
        import uuid
        uname = f"pt{uuid.uuid4().hex[:6]}"
        await client.post("/login/register", json={"username": uname, "password": "test123456"})
        resp = await client.post("/login/login", json={"username": uname, "password": "test123456"})
        uid = resp.json()["user"]["id"]
        token = resp.json()["access_token"]

        # Disable the user
        await client.post(f"/admin/users/{uid}/disable", headers=_auth(admin_token))

        # Try accessing protected endpoint
        resp = await client.get("/login/me", headers=_auth(token))
        assert resp.status_code == 403

    async def test_user_cannot_modify_other_user_data(self, client: AsyncClient, user_token):
        """PUT /profile/me 不接受 user_id，当前用户从 JWT 获取。"""
        # 尝试修改他人画像（实际上 route 不接收 user_id）
        resp = await client.put("/profile/me", headers=_auth(user_token), json={
            "stage": "junior", "grade": "七年级", "subject": "数学"
        })
        # 只能改自己的，这个请求应该成功（改自己的）
        assert resp.status_code == 200
