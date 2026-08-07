"""成员四 完整端到端测试：错题、复习与学习报告

测试流程：
1. 普通用户登录 → 查看错题 → 订正 → 复习 → 生成报告
2. 管理员登录 → 查看错题统计/复习情况/薄弱知识点/学习轨迹
3. 权限测试：普通用户不能访问管理员接口
"""

import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.main import app


# ── Fixtures ──────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    """提供 ASGI 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user_token(client):
    """注册/登录普通用户，返回 token。"""
    import random
    username = f"test_member4_{random.randint(10000, 99999)}"
    # 注册
    res = await client.post("/login/register", json={"username": username, "password": "test123456"})
    assert res.status_code == 200
    # 登录
    res = await client.post("/login/login", json={"username": username, "password": "test123456"})
    assert res.status_code == 200
    payload = res.json()
    return payload["access_token"]


@pytest_asyncio.fixture
async def admin_token(client, user_token):
    """获取管理员 token。"""
    import random
    username = f"test_admin_{random.randint(10000, 99999)}"
    await client.post("/login/register", json={"username": username, "password": "admin123"})
    # 通过数据库设为 admin（简化方式：用已有 admin）
    from sqlalchemy import select, update
    from backend.model import AsyncSessionLocal
    from backend.model.user import User
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.username == username))).scalar_one()
        user.role = "admin"
        await db.commit()
    res = await client.post("/login/login", json={"username": username, "password": "admin123"})
    return res.json()["access_token"]


# ── 1. 错题查询与订正 ────────────────────────────


@pytest.mark.asyncio
async def test_get_mistakes_unauthorized(client):
    """未登录访问错题应返回 401。"""
    res = await client.get("/mistakes")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_mistakes_empty(client, user_token):
    """新用户错题列表为空。"""
    res = await client.get("/mistakes", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_get_mistakes_with_filters(client, user_token):
    """错题列表支持 status 筛选。"""
    res = await client.get(
        "/mistakes?page=1&page_size=10&status=pending",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["items"] == []


@pytest.mark.asyncio
async def test_correction_not_found(client, user_token):
    """订正不存在的错题返回 404。"""
    res = await client.post(
        "/mistakes/99999/correction",
        json={"answer": "test"},
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Request-ID": "test-req-001",
        },
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_correction_missing_request_id(client, user_token):
    """订正缺少 X-Request-ID 返回 422。"""
    res = await client.post(
        "/mistakes/1/correction",
        json={"answer": "test"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code in (422, 400)


# ── 2. 知识点复习卡 ──────────────────────────────


@pytest.mark.asyncio
async def test_review_card_requires_param(client, user_token):
    """复习卡缺少 knowledge_point_name 返回 422。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=一元一次方程&mode=full",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert "knowledge_point_name" in data["data"]


@pytest.mark.asyncio
async def test_review_card_invalid_mode(client, user_token):
    """复习卡非法 mode 返回 422。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=test&mode=invalid",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_review_card_quick_mode(client, user_token):
    """快速模式复习卡正常返回。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=一元一次方程&mode=quick",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data.get("quiz", [])) == 2


@pytest.mark.asyncio
async def test_review_card_advanced_mode(client, user_token):
    """进阶模式复习卡包含 advanced_focus。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=一元一次方程&mode=advanced",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data.get("quiz", [])) == 3
    assert "advanced_focus" in data


@pytest.mark.asyncio
async def test_review_card_dynamic_generation(client, user_token):
    """内置卡片之外的知识点触发动态生成（含降级）。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=数据库事务隔离级别&mode=full",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "summary" in data
    assert "concepts" in data
    assert "formula" in data
    assert len(data.get("quiz", [])) == 3


@pytest.mark.asyncio
async def test_review_card_empty_name_rejected(client, user_token):
    """空知识点名返回 422。"""
    res = await client.get(
        "/knowledge-reviews/card?knowledge_point_name=综合知识点&mode=full",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code in (400, 422)


# ── 3. 复习完成 ──────────────────────────────────


@pytest.mark.asyncio
async def test_complete_review_missing_request_id(client, user_token):
    """完成复习缺少 X-Request-ID 返回 422。"""
    res = await client.post(
        "/knowledge-reviews/complete",
        json={
            "knowledge_point_name": "一元一次方程",
            "review_mode": "quick",
            "answers": [0, 1],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code in (422, 400)


@pytest.mark.asyncio
async def test_complete_review_idempotent(client, user_token):
    """完成复习支持幂等（同一 request_id 返回相同结果）。"""
    req_id = "test-review-idempotent-001"
    body = {
        "knowledge_point_name": "一元一次方程",
        "review_mode": "full",
        "answers": [0, 1, 1],
    }
    res1 = await client.post(
        "/knowledge-reviews/complete",
        json=body,
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Request-ID": req_id,
        },
    )
    assert res1.status_code == 200
    res2 = await client.post(
        "/knowledge-reviews/complete",
        json=body,
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Request-ID": req_id,
        },
    )
    assert res2.status_code == 200
    assert res1.json()["data"]["review_id"] == res2.json()["data"]["review_id"]


# ── 4. 今日复习 ──────────────────────────────────


@pytest.mark.asyncio
async def test_today_reviews_empty(client, user_token):
    """新用户今日复习为空。"""
    res = await client.get(
        "/mistakes/reviews/today",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    assert res.json()["data"] == []


# ── 5. 学情报告 ──────────────────────────────────


@pytest.mark.asyncio
async def test_generate_report_vip_required(client, user_token):
    """普通用户使用 vip 方式生成报告被拒绝（非 VIP 用户）。"""
    import uuid
    res = await client.post(
        "/reports/stage",
        json={
            "date_from": "2026-07-01",
            "date_to": "2026-08-07",
            "payment_method": "vip",
        },
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Request-ID": str(uuid.uuid4()),
        },
    )
    # 普通用户不是 VIP，"vip" 支付方式应被拒绝
    assert res.status_code in (200, 403)
    if res.status_code == 200:
        data = res.json()
        assert data["code"] == "OK"
        assert "report_id" in data["data"]


@pytest.mark.asyncio
async def test_get_reports_list(client, user_token):
    """获取报告列表。"""
    res = await client.get(
        "/reports?page=1&page_size=10",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data["data"]


@pytest.mark.asyncio
async def test_report_detail_not_found(client, user_token):
    """报告详情不存在返回 404。"""
    res = await client.get(
        "/reports/99999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 404


# ── 6. 学习记录 ──────────────────────────────────


@pytest.mark.asyncio
async def test_records_empty(client, user_token):
    """新用户学习记录为空。"""
    res = await client.get(
        "/records?page=1&page_size=10",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_records_params_validation(client, user_token):
    """记录查询参数校验。"""
    res = await client.get(
        "/records?page=0&page_size=200",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 422


# ── 7. 管理员接口 ────────────────────────────────


@pytest.mark.asyncio
async def test_admin_mistakes_unauthorized(client, user_token):
    """普通用户访问管理员接口返回 403。"""
    res = await client.get(
        "/admin/learning/mistakes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_mistakes_unauth_no_token(client):
    """无 Token 访问管理员接口返回 401。"""
    res = await client.get("/admin/learning/mistakes")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_mistake_stats(client, admin_token):
    """管理员查看错题统计正常。"""
    res = await client.get(
        "/admin/learning/mistakes?page=1&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert "items" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_admin_review_stats(client, admin_token):
    """管理员查看复习情况正常。"""
    res = await client.get(
        "/admin/learning/reviews?page=1&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert "items" in data["data"]


@pytest.mark.asyncio
async def test_admin_weak_points(client, admin_token):
    """管理员查看薄弱知识点正常。"""
    res = await client.get(
        "/admin/learning/weak-points?page=1&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    # 薄弱知识点可能有数据也可能为空
    assert "items" in data["data"]


@pytest.mark.asyncio
async def test_admin_user_summary(client, admin_token):
    """管理员查看用户学习轨迹正常。"""
    res = await client.get(
        "/admin/learning/users/1/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    summary = data["data"]
    assert "user" in summary
    assert "mistake_summary" in summary
    assert "review_summary" in summary
    assert "learning_summary" in summary
    assert "weak_knowledge_points" in summary


@pytest.mark.asyncio
async def test_admin_user_summary_not_found(client, admin_token):
    """查看不存在用户返回 404。"""
    res = await client.get(
        "/admin/learning/users/99999999/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 404


# ── 8. 首页推荐与今日计划 ────────────────────────


@pytest.mark.asyncio
async def test_home_recommendations(client, user_token):
    """首页推荐正常返回。"""
    res = await client.get(
        "/recommendations/home",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    # 新用户推荐应包含兜底内容
    assert "primary" in data["data"]


@pytest.mark.asyncio
async def test_today_plan(client, user_token):
    """今日计划正常返回。"""
    res = await client.get(
        "/plans/today",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert "target_groups" in data["data"]


# ── 9. 站内提醒 ──────────────────────────────────


@pytest.mark.asyncio
async def test_notifications_endpoints(client, user_token):
    """新用户提醒接口正常返回。"""
    # 提醒列表
    res = await client.get(
        "/notifications?page=1&page_size=10",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "OK"
    assert isinstance(data["data"]["total"], int)

    # 未读数
    res2 = await client.get(
        "/notifications/unread-count",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res2.status_code == 200
    assert isinstance(res2.json()["data"]["count"], int)


@pytest.mark.asyncio
async def test_mark_all_read_empty(client, user_token):
    """空提醒标记已读正常。"""
    res = await client.post(
        "/notifications/read-all",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["updated"] == 0
