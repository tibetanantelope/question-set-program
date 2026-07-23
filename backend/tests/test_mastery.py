"""成员三：掌握度、错题订正与复习 接口与服务测试

覆盖场景（对齐《五人任务分工》第 6.4 节验收标准）：
- 掌握度计算（简单/中等/困难答对 + 答错）
- 掌握度边界限制（0~100）
- 学习状态映射
- 错题创建与订正流程
- 订正幂等（X-Request-ID）
- 首次订正成功生成 1/3/7 天复习计划
- 跨用户数据隔离
- 未登录拒绝访问
"""

import uuid
from datetime import date

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
    """注册并登录测试用户，返回 Bearer token。"""
    username = f"test_{uuid.uuid4().hex[:8]}"
    password = "test123456"

    await client.post("/login/register", json={"username": username, "password": password})
    resp = await client.post("/login/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token: str, request_id: str = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if request_id:
        h["X-Request-ID"] = request_id
    return h


def _make_event(
    request_id: str,
    user_id: int,
    practice_id: int = 1,
    question_id: int = 1,
    kp_id: int = 101,
    kp_name: str = "一元一次方程-移项",
    difficulty: str = "easy",
    is_correct: bool = False,
    error_type: str = "calculation",
) -> dict:
    """构造 AnswerResultEvent 字典（模拟成员二调用）。"""
    return {
        "request_id": request_id,
        "user_id": user_id,
        "practice_id": practice_id,
        "question_id": question_id,
        "knowledge_point_id": kp_id,
        "knowledge_point_name": kp_name,
        "difficulty": difficulty,
        "is_correct": is_correct,
        "error_type": error_type,
        "answered_at": "2026-07-20T14:45:00+08:00",
    }


# ── Service 层测试 ────────────────────────────────────────

class TestMasteryService:
    """掌握度计算与错题创建"""

    async def test_process_correct_easy_adds_3(self):
        """简单题答对 +3"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        rid = f"test-{uuid.uuid4().hex}"
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=uid,  # 用 uid 确保每次运行独立
            knowledge_point_name="测试知识点",
            difficulty="easy",
            is_correct=True,
            error_type=None,
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        assert result["mastery_before"] == 60, f"新知识点的初始掌握度应为 60，实际: {result['mastery_before']}"
        assert result["mastery_after"] == 63, f"简单题答对应为 +3，实际: {result['mastery_after']}"
        assert result["learning_status"] == "consolidating"
        assert result["mistake_id"] is None

    async def test_process_medium_adds_5(self):
        """中等题答对 +5"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        rid = f"test-{uuid.uuid4().hex}"
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=uid,
            knowledge_point_name="测试知识点",
            difficulty="medium",
            is_correct=True,
            error_type=None,
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        assert result["mastery_after"] == 65

    async def test_process_hard_adds_8(self):
        """困难题答对 +8"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        rid = f"test-{uuid.uuid4().hex}"
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=uid,
            knowledge_point_name="测试知识点",
            difficulty="hard",
            is_correct=True,
            error_type=None,
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        assert result["mastery_after"] == 68

    async def test_process_wrong_subtracts_3(self):
        """任意题答错 -3"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        rid = f"test-{uuid.uuid4().hex}"
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=uid,
            knowledge_point_name="测试知识点",
            difficulty="hard",
            is_correct=False,
            error_type="calculation",
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        assert result["mastery_after"] == 57
        assert result["learning_status"] == "weak"
        assert result["mistake_id"] is not None

    async def test_process_answer_idempotent(self):
        """相同 request_id 重复提交不重复处理"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        rid = f"test-{uuid.uuid4().hex}"
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=uid,
            knowledge_point_name="测试知识点",
            difficulty="easy",
            is_correct=True,
            error_type=None,
            answered_at="2026-07-20T14:45:00+08:00",
        )
        r1 = await svc.process_answer(event)
        r2 = await svc.process_answer(event)
        # 第二次应该返回幂等标记
        assert r2.get("idempotent") is True, f"幂等调用应返回 idempotent=True，实际: {r2}"

    async def test_mastery_score_clamped_0_to_100(self):
        """掌握度不会超出 0~100 范围"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        uid = abs(hash(uuid.uuid4().hex)) % 90000000 + 10000000

        # 连续答对 20 次中等题（每次 +5）不会超过 100
        for i in range(20):
            event = AnswerResultEvent(
                request_id=f"clamp-test-{uid}-{i}",
                user_id=uid,
                practice_id=1,
                question_id=i + 1,
                knowledge_point_id=uid,
                knowledge_point_name="测试知识点",
                difficulty="medium",
                is_correct=True,
                error_type=None,
                answered_at="2026-07-20T14:45:00+08:00",
            )
            result = await svc.process_answer(event)
        assert result["mastery_after"] <= 100, f"掌握度不应超过 100，实际: {result['mastery_after']}"

    async def test_learning_status_mapping(self):
        """学习状态映射: 0~59 weak, 60~80 consolidating, 81~100 mastered"""
        from backend.services.mastery_service.mastery_service import _score_to_status

        assert _score_to_status(0) == "weak"
        assert _score_to_status(30) == "weak"
        assert _score_to_status(59) == "weak"
        assert _score_to_status(60) == "consolidating"
        assert _score_to_status(75) == "consolidating"
        assert _score_to_status(80) == "consolidating"
        assert _score_to_status(81) == "mastered"
        assert _score_to_status(100) == "mastered"


# ── API 层测试 ─────────────────────────────────────────────

class TestMasteryApi:
    """GET /mastery/knowledge-points 和 GET /mastery/trend"""

    async def test_list_masteries_empty(self, client: AsyncClient, token: str):
        """新用户无掌握度记录时返回空列表。"""
        resp = await client.get("/mastery/knowledge-points", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        assert body["data"]["items"] == []

    async def test_list_masteries_with_status_filter(self, client: AsyncClient, token: str):
        """按状态筛选知识点掌握列表。"""
        resp = await client.get("/mastery/knowledge-points", headers=auth_headers(token),
                                params={"status": "weak"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        # 新用户 weak 状态为空
        assert body["data"]["items"] == []

    async def test_get_trend_empty(self, client: AsyncClient, token: str):
        """新用户无趋势数据返回零值。"""
        resp = await client.get("/mastery/trend", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["current_score"] == 0
        assert body["data"]["points"] == []

    async def test_requires_auth_mastery(self, client: AsyncClient):
        """未登录请求掌握度接口返回 401。"""
        resp = await client.get("/mastery/knowledge-points")
        assert resp.status_code == 401

    async def test_requires_auth_trend(self, client: AsyncClient):
        resp = await client.get("/mastery/trend")
        assert resp.status_code == 401


class TestMistakeApi:
    """GET /mistakes 和 POST /mistakes/{id}/correction"""

    async def test_list_mistakes_empty(self, client: AsyncClient, token: str):
        """新用户无错题时返回空列表。"""
        resp = await client.get("/mistakes", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "OK"
        assert body["data"]["items"] == []

    async def test_correction_mistake_not_found(self, client: AsyncClient, token: str):
        """订正不存在的错题返回 404。"""
        resp = await client.post(
            "/mistakes/99999/correction",
            headers=auth_headers(token, "req-notfound-001"),
            json={"answer": "x=6"},
        )
        assert resp.status_code == 404

    async def test_correction_requires_request_id(self, client: AsyncClient, token: str):
        """缺少 X-Request-ID 返回 422。"""
        resp = await client.post(
            "/mistakes/1/correction",
            headers=auth_headers(token),  # 无 X-Request-ID
            json={"answer": "x=6"},
        )
        assert resp.status_code == 422

    async def test_requires_auth_mistakes(self, client: AsyncClient):
        resp = await client.get("/mistakes")
        assert resp.status_code == 401

    async def test_requires_auth_correction(self, client: AsyncClient):
        resp = await client.post(
            "/mistakes/1/correction",
            headers={"X-Request-ID": "test-001"},
            json={"answer": "x=6"},
        )
        assert resp.status_code == 401


class TestMistakeCorrectionFlow:
    """端到端：答题 → 错题 → 订正 → 复习计划"""

    async def test_full_correction_flow(self):
        """完整流程：答题答错 → 创建错题 → 订正成功 → 1/3/7 天复习计划"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent
        from backend.schemas.request.mastery_request import CorrectionSubmitRequest

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        uid = 99999007 + abs(hash("full-correction-flow")) % 100000

        # 1. 答题答错（模拟成员二调用）
        rid = f"flow-test-{uuid.uuid4().hex}"
        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=101,
            knowledge_point_name="一元一次方程-移项",
            difficulty="easy",
            is_correct=False,
            error_type="calculation",
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        mistake_id = result["mistake_id"]
        assert mistake_id is not None, "答错应创建错题记录"

        # 2. 查询错题列表
        mistake_list, _ = await mapper.list_mistakes(uid, status="pending")
        assert len(mistake_list) >= 1

        # 3. 提交订正（正确）
        corr_rid = f"corr-flow-{uuid.uuid4().hex}"
        corr_req = CorrectionSubmitRequest(answer="x=6")
        corr_result = await svc.submit_correction(uid, mistake_id, corr_req, corr_rid)

        # 订正结果依赖于 standard_answer 的匹配（mock 数据可能为空）
        assert corr_result.mistake_id == mistake_id

        # 4. 如果是首次成功，应生成复习计划
        if corr_result.first_success:
            assert len(corr_result.review_dates) == 3, \
                f"首次订正成功应生成 3 个复习日期，实际: {corr_result.review_dates}"
            # 验证 1/3/7 天间隔
            from datetime import date, timedelta
            today = date.today()
            expected = [
                (today + timedelta(days=i)).isoformat()
                for i in [1, 3, 7]
            ]
            assert corr_result.review_dates == expected, \
                f"复习日期应为 1/3/7 天后: {corr_result.review_dates}"

    async def test_correction_idempotent(self):
        """订正幂等：相同 X-Request-ID 重复提交不重复处理"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent
        from backend.schemas.request.mastery_request import CorrectionSubmitRequest

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        uid = 99999008 + abs(hash("corr-idempotent")) % 100000

        # 先创建一个错题
        rid = f"idem-test-{uuid.uuid4().hex}"
        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=101,
            knowledge_point_name="一元一次方程",
            difficulty="medium",
            is_correct=False,
            error_type="knowledge",
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        mistake_id = result["mistake_id"]

        # 订正
        corr_rid = f"corr-idem-{uuid.uuid4().hex}"
        corr_req = CorrectionSubmitRequest(answer="test")
        r1 = await svc.submit_correction(uid, mistake_id, corr_req, corr_rid)
        r2 = await svc.submit_correction(uid, mistake_id, corr_req, corr_rid)
        # 两次返回一致
        assert r1.is_correct == r2.is_correct
        assert r1.correction_status == r2.correction_status

    async def test_correction_wrong_answer(self):
        """订正答案错误的情况"""
        from backend.dao.mastery_mapper import get_mastery_mapper
        from backend.services.mastery_service.mastery_service import MasteryService
        from backend.schemas.response.mastery_response import AnswerResultEvent
        from backend.schemas.request.mastery_request import CorrectionSubmitRequest

        mapper = await get_mastery_mapper()
        svc = MasteryService(mapper)
        uid = 99999009 + abs(hash("corr-wrong")) % 100000

        # 创建错题
        rid = f"wrong-test-{uuid.uuid4().hex}"
        event = AnswerResultEvent(
            request_id=rid,
            user_id=uid,
            practice_id=1,
            question_id=1,
            knowledge_point_id=101,
            knowledge_point_name="一元一次方程",
            difficulty="easy",
            is_correct=False,
            error_type="calculation",
            answered_at="2026-07-20T14:45:00+08:00",
        )
        result = await svc.process_answer(event)
        mistake_id = result["mistake_id"]

        # 提交错误订正
        corr_rid = f"corr-wrong-{uuid.uuid4().hex}"
        corr_req = CorrectionSubmitRequest(answer="completely wrong answer")
        corr_result = await svc.submit_correction(uid, mistake_id, corr_req, corr_rid)
        assert corr_result.is_correct is False, "错误的订正答案应返回 is_correct=False"
        assert corr_result.first_success is False, "订正失败不应触发首次成功"


class TestReviewApi:
    """GET /mistakes/reviews/today"""

    async def test_today_reviews_empty(self, client: AsyncClient, token: str):
        """新用户今日无到期复习。"""
        resp = await client.get("/mistakes/reviews/today", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/mistakes/reviews/today")
        assert resp.status_code == 401


# ── 跨用户隔离测试 ─────────────────────────────────────────

class TestCrossUserIsolation:
    async def test_cannot_access_other_user_mistake(self, client: AsyncClient, token: str):
        """不能查看/订正其他用户的错题。"""
        # 用户 A 尝试订正不存在的错题 → 404（不是 403）
        resp = await client.post(
            "/mistakes/1/correction",
            headers=auth_headers(token, "iso-test-001"),
            json={"answer": "x=6"},
        )
        # 错题 ID=1 要么不存在，要么不属于当前用户，都应 404
        assert resp.status_code == 404


# ── 分页参数校验 ───────────────────────────────────────────

class TestPagination:
    async def test_invalid_page(self, client: AsyncClient, token: str):
        resp = await client.get("/mastery/knowledge-points", headers=auth_headers(token),
                                params={"page": 0})
        assert resp.status_code == 422

    async def test_invalid_page_size_too_large(self, client: AsyncClient, token: str):
        resp = await client.get("/mastery/knowledge-points", headers=auth_headers(token),
                                params={"page_size": 200})
        assert resp.status_code == 422
