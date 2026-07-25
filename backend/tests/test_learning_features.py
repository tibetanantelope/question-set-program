"""成员四功能测试：学习记录、首页推荐、学习报告、学习提醒"""

import os
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault(
    "SQL_DATABASE_URL",
    "mysql+asyncmy://test:test@127.0.0.1:3306/test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")


# ============================================================
# 辅助工具
# ============================================================

class _AsyncCtx:
    """将 AsyncMock 转为 async context manager"""
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        pass


def _patch_session(monkeypatch, module_path: str, session: AsyncMock):
    """替换目标模块中的 AsyncSessionLocal"""
    monkeypatch.setattr(
        f"{module_path}.AsyncSessionLocal",
        lambda: _AsyncCtx(session),
    )


# ============================================================
# 测试 1：学习记录查询
# ============================================================

@pytest.mark.asyncio
async def test_get_records_returns_paginated_items(monkeypatch):
    """分页查询学习记录，返回正确的数量和结构"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    class FakeRecord:
        def __init__(self, rid, rtype, title, accuracy):
            self.id = rid
            self.record_type = rtype
            self.title = title
            self.subject = "数学"
            self.knowledge_point_name = "一元一次方程"
            self.question_count = 5
            self.correct_count = 3
            self.accuracy = accuracy
            self.mastery_change = 2
            self.occurred_at = datetime(2026, 7, 20, 14, 30)

    fake_records = [
        FakeRecord(1, "practice", "练习1", 60.0),
        FakeRecord(2, "correction", "订正1", 100.0),
        FakeRecord(3, "practice", "练习2", 80.0),
    ]

    session = AsyncMock()
    session.execute = AsyncMock()

    # Mock 1: count query → scalar()
    count_result = MagicMock()
    count_result.scalar.return_value = 3

    # Mock 2: data query → scalars() → all()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = fake_records
    rows_result = MagicMock()
    rows_result.scalars.return_value = scalars_mock

    session.execute.side_effect = [count_result, rows_result]
    _patch_session(monkeypatch, "backend.services.record_service", session)

    items, total, pages = await svc.get_records(user_id=7, page=1, page_size=20)

    assert total == 3
    assert len(items) == 3
    assert items[0]["record_id"] == 1
    assert items[0]["record_type"] == "practice"
    assert items[0]["accuracy"] == 60.0


# ============================================================
# 测试 2：学习记录统计摘要
# ============================================================

@pytest.mark.asyncio
async def test_get_stats_summary_returns_correct_values(monkeypatch):
    """统计摘要返回正确的聚合值"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()

    c1 = MagicMock(); c1.scalar.return_value = 10   # practice_count
    c2 = MagicMock(); c2.scalar.return_value = 50   # question_count
    c3 = MagicMock(); c3.scalar.return_value = 75.5 # avg_accuracy
    c4 = MagicMock(); c4.scalar.return_value = 8    # mastery_change
    session.execute.side_effect = [c1, c2, c3, c4]

    _patch_session(monkeypatch, "backend.services.record_service", session)

    stats = await svc.get_stats_summary(user_id=7)

    assert stats["practice_count"] == 10
    assert stats["question_count"] == 50
    assert stats["avg_accuracy"] == 75.5
    assert stats["mastery_change"] == 8


# ============================================================
# 测试 3：练习记录幂等性
# ============================================================

@pytest.mark.asyncio
async def test_record_practice_skips_invalid_event():
    """is_valid=False 时跳过记录"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    class InvalidEvent:
        is_valid = False
        user_id = 7

    result = await svc.record_practice(InvalidEvent())
    assert result is None


@pytest.mark.asyncio
async def test_record_practice_idempotent(monkeypatch):
    """相同 request_id 不会重复插入"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()
    # 幂等检查：已存在记录
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = MagicMock()
    session.execute.return_value = existing

    _patch_session(monkeypatch, "backend.services.record_service", session)

    class ValidEvent:
        is_valid = True
        user_id = 7
        subject = "数学"
        knowledge_point_name = "方程"
        question_count = 5
        correct_count = 3
        accuracy = 60.0
        request_id = "req-001"
        completed_at = datetime(2026, 7, 22, 10, 0)

    result = await svc.record_practice(ValidEvent())
    assert result is None  # 幂等跳过
    session.commit.assert_not_awaited()


# ============================================================
# 测试 4：今日计划
# ============================================================

@pytest.mark.asyncio
async def test_get_today_plan_creates_new_plan(monkeypatch):
    """首次获取今日计划时自动创建"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()

    # 计划不存在
    plan_check = MagicMock()
    plan_check.scalar_one_or_none.return_value = None

    # 用户画像不存在（取默认值 3）
    profile_check = MagicMock()
    profile_check.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(side_effect=[plan_check, profile_check])
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    _patch_session(monkeypatch, "backend.services.record_service", session)

    plan = await svc.get_today_plan(user_id=7)

    assert plan["target_groups"] == 3
    assert plan["completed_groups"] == 0
    assert plan["completed"] is False
    assert len(plan["tasks"]) >= 1
    session.commit.assert_awaited_once()


# ============================================================
# 测试 5：通知 CRUD
# ============================================================

@pytest.mark.asyncio
async def test_create_notification(monkeypatch):
    """创建通知返回新 ID"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def fake_refresh(n):
        n.id = 99
        n.type = "review_due"
        n.title = "测试通知"
        n.content = "测试内容"
        n.is_read = 0
        n.created_at = datetime(2026, 7, 22, 9, 0)
    session.refresh = fake_refresh

    _patch_session(monkeypatch, "backend.services.record_service", session)

    nid = await svc.create_notification(7, "review_due", "测试通知", "测试内容")
    assert nid == 99


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(monkeypatch):
    """标记不存在的通知抛出 BusinessError"""
    from backend.services.record_service import RecordService
    from backend.core.exceptions import BusinessError

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    session.execute.return_value = not_found

    _patch_session(monkeypatch, "backend.services.record_service", session)

    with pytest.raises(BusinessError) as exc:
        await svc.mark_notification_read(7, 999)
    assert exc.value.code == "NOTIFICATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_unread_count(monkeypatch):
    """未读计数返回正确数值"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 5
    session.execute.return_value = count_result

    _patch_session(monkeypatch, "backend.services.record_service", session)

    count = await svc.get_unread_count(user_id=7)
    assert count == 5


@pytest.mark.asyncio
async def test_mark_all_notifications_read(monkeypatch):
    """批量标记已读返回更新数量"""
    from backend.services.record_service import RecordService
    from backend.model.learning_models import Notification

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()

    # 构造两条未读通知
    n1 = Notification(id=1, user_id=7, type="review_due", title="t1", is_read=0)
    n2 = Notification(id=2, user_id=7, type="daily_plan", title="t2", is_read=0)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [n1, n2]
    session.execute.return_value = result_mock
    session.commit = AsyncMock()

    _patch_session(monkeypatch, "backend.services.record_service", session)

    count = await svc.mark_all_notifications_read(user_id=7)
    assert count == 2
    assert n1.is_read == 1
    assert n2.is_read == 1


# ============================================================
# 测试 6：报告生成
# ============================================================

@pytest.mark.asyncio
async def test_generate_report_creates_new(monkeypatch):
    """生成新报告成功返回报告数据"""
    from backend.services.report_service import ReportService

    svc = ReportService()

    # ---- 幂等检查 session ----
    session1 = AsyncMock()
    session1.execute = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session1.execute.return_value = no_existing

    # ---- _gather_stats session ----
    session2 = AsyncMock()
    session2.execute = AsyncMock()
    stats_row = MagicMock()
    stats_row.practice_cnt = 5
    stats_row.question_cnt = 20
    stats_row.avg_acc = 72.5
    stats_row.total_mastery_change = 10
    stats_result = MagicMock()
    stats_result.fetchone.return_value = stats_row
    session2.execute.return_value = stats_result

    # ---- _get_frequent_error session ----
    session3 = AsyncMock()
    session3.execute = AsyncMock()
    error_result = MagicMock()
    error_result.fetchone.return_value = ["calculation"]
    session3.execute.return_value = error_result

    # ---- _get_weak_points session ----
    session4 = AsyncMock()
    session4.execute = AsyncMock()
    weak_row = MagicMock()
    weak_row.knowledge_point_name = "去括号"
    weak_list_result = MagicMock()
    weak_list_result.all.return_value = [weak_row]
    session4.execute.return_value = weak_list_result

    # ---- 持久化 session ----
    session5 = AsyncMock()
    session5.add = MagicMock()
    session5.commit = AsyncMock()

    async def fake_refresh(r):
        r.id = 42
        r.date_from = date(2026, 7, 16)
        r.date_to = date(2026, 7, 22)
        r.practice_count = 5
        r.question_count = 20
        r.accuracy = 72.5
        r.mastery_change = 10
        r.frequent_error_type = "calculation"
        r.weak_points = ["去括号"]
        r.suggestion = "测试建议"
        r.created_at = datetime(2026, 7, 22, 18, 0)
    session5.refresh = fake_refresh

    # AsyncSessionLocal 会被调用 5 次，每次返回不同的 session
    call_count = [0]
    sessions = [session1, session2, session3, session4, session5]

    def session_factory():
        idx = call_count[0]
        call_count[0] += 1
        return _AsyncCtx(sessions[min(idx, len(sessions) - 1)])

    monkeypatch.setattr(
        "backend.services.report_service.AsyncSessionLocal",
        session_factory,
    )

    report = await svc.generate_report(
        user_id=7,
        date_from="2026-07-16",
        date_to="2026-07-22",
        request_id="rpt-001",
    )

    assert report["report_id"] == 42
    assert report["practice_count"] == 5
    assert report["accuracy"] == 72.5
    assert report["weak_points"] == ["去括号"]


@pytest.mark.asyncio
async def test_generate_report_idempotent(monkeypatch):
    """相同 request_id 返回已有报告不重复创建"""
    from backend.services.report_service import ReportService
    from backend.model.learning_models import LearningReport

    svc = ReportService()

    existing_report = LearningReport(
        id=10, user_id=7, date_from=date(2026, 7, 16), date_to=date(2026, 7, 22),
        practice_count=3, question_count=10, accuracy=80.0, mastery_change=5,
        request_id="rpt-002",
    )

    session = AsyncMock()
    session.execute = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_report
    session.execute.return_value = existing_result

    monkeypatch.setattr(
        "backend.services.report_service.AsyncSessionLocal",
        lambda: _AsyncCtx(session),
    )

    report = await svc.generate_report(
        user_id=7, date_from="2026-07-16", date_to="2026-07-22", request_id="rpt-002",
    )

    assert report["report_id"] == 10
    assert report["practice_count"] == 3


# ============================================================
# 测试 7：报告建议生成
# ============================================================

def test_generate_suggestion_low_accuracy():
    from backend.services.report_service import ReportService
    svc = ReportService()
    suggestion = svc._generate_suggestion(
        stats={"accuracy": 45.0}, frequent_error="calculation", weak_points=["方程"],
    )
    assert "正确率偏低" in suggestion
    assert "计算" in suggestion


def test_generate_suggestion_high_accuracy():
    from backend.services.report_service import ReportService
    svc = ReportService()
    suggestion = svc._generate_suggestion(
        stats={"accuracy": 85.0}, frequent_error=None, weak_points=[],
    )
    assert "正确率表现良好" in suggestion


def test_generate_suggestion_knowledge_error():
    from backend.services.report_service import ReportService
    svc = ReportService()
    suggestion = svc._generate_suggestion(
        stats={"accuracy": 70.0}, frequent_error="knowledge", weak_points=["移项"],
    )
    assert "回顾相关概念" in suggestion


# ============================================================
# 测试 8：API 端点
# ============================================================

@pytest.fixture
def test_app():
    app = FastAPI()
    from backend.middleware.exception import register_exception_handlers
    register_exception_handlers(app)
    return app


def test_get_records_endpoint_returns_success(test_app, monkeypatch):
    """GET /records 返回统一响应格式"""
    from backend.services.record_service import RecordService
    from backend.api.records_api import records_router
    from backend.api.dependencies import get_current_user
    from backend.model.user import User

    svc = RecordService()

    async def fake_get_records(*args, **kwargs):
        return ([{"record_id": 1, "record_type": "practice", "title": "测试"}], 1, 1)
    svc.get_records = fake_get_records

    test_app.dependency_overrides[get_current_user] = lambda: User(id=7, username="test", password="x")
    monkeypatch.setattr("backend.api.records_api", "record_service", svc)
    test_app.include_router(records_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get(
            "/records?page=1&page_size=10",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "OK"
    assert body["data"]["total"] == 1
    test_app.dependency_overrides.clear()


def test_get_unread_count_endpoint(test_app, monkeypatch):
    """GET /notifications/unread-count 返回未读数"""
    from backend.services.record_service import RecordService
    from backend.api.records_api import records_router
    from backend.api.dependencies import get_current_user
    from backend.model.user import User

    svc = RecordService()
    svc.get_unread_count = AsyncMock(return_value=3)

    test_app.dependency_overrides[get_current_user] = lambda: User(id=7, username="test", password="x")
    monkeypatch.setattr("backend.api.records_api", "record_service", svc)
    test_app.include_router(records_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get(
            "/notifications/unread-count",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["count"] == 3
    test_app.dependency_overrides.clear()


def test_notifications_read_all_endpoint(test_app, monkeypatch):
    """POST /notifications/read-all 返回更新数量"""
    from backend.services.record_service import RecordService
    from backend.api.records_api import records_router
    from backend.api.dependencies import get_current_user
    from backend.model.user import User

    svc = RecordService()
    svc.mark_all_notifications_read = AsyncMock(return_value=5)

    test_app.dependency_overrides[get_current_user] = lambda: User(id=7, username="test", password="x")
    monkeypatch.setattr("backend.api.records_api", "record_service", svc)
    test_app.include_router(records_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/notifications/read-all",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["updated"] == 5
    test_app.dependency_overrides.clear()


def test_reports_endpoint_generate(test_app, monkeypatch):
    """POST /reports/stage 生成报告"""
    from backend.services.report_service import ReportService
    from backend.api.reports_api import reports_router
    from backend.api.dependencies import get_current_user
    from backend.model.user import User

    svc = ReportService()
    svc.generate_report = AsyncMock(return_value={
        "report_id": 1, "date_from": "2026-07-16", "date_to": "2026-07-22",
        "practice_count": 5, "question_count": 20, "accuracy": 75.0,
        "mastery_change": 8, "frequent_error_type": None, "weak_points": [],
        "suggestion": "继续保持", "created_at": "2026-07-22T18:00:00",
    })

    async def fake_entitlement(*args, **kwargs):
        return None

    test_app.dependency_overrides[get_current_user] = lambda: User(id=7, username="test", password="x")
    monkeypatch.setattr("backend.api.reports_api", "report_service", svc)
    monkeypatch.setattr("backend.api.reports_api", "_check_report_entitlement", fake_entitlement)
    test_app.include_router(reports_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/reports/stage",
            json={"date_from": "2026-07-16", "date_to": "2026-07-22", "payment_method": "vip"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "OK"
    assert body["data"]["report_id"] == 1
    test_app.dependency_overrides.clear()


def test_reports_list_endpoint(test_app, monkeypatch):
    """GET /reports 返回报告列表"""
    from backend.services.report_service import ReportService
    from backend.api.reports_api import reports_router
    from backend.api.dependencies import get_current_user
    from backend.model.user import User

    svc = ReportService()
    svc.get_reports = AsyncMock(return_value=(
        [{"report_id": 1, "date_from": "2026-07-16", "date_to": "2026-07-22",
          "practice_count": 5, "accuracy": 75.0, "created_at": "2026-07-22T18:00:00"}],
        1, 1,
    ))

    test_app.dependency_overrides[get_current_user] = lambda: User(id=7, username="test", password="x")
    monkeypatch.setattr("backend.api.reports_api", "report_service", svc)
    test_app.include_router(reports_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get(
            "/reports?page=1&page_size=10",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    test_app.dependency_overrides.clear()


def test_unauthorized_access_returns_401(test_app):
    """未认证请求返回 401"""
    from backend.api.records_api import records_router

    test_app.include_router(records_router)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/records")
    assert response.status_code == 401


# ============================================================
# 测试 9：首页推荐降级
# ============================================================

@pytest.mark.asyncio
async def test_fallback_low_mastery_returns_items(monkeypatch):
    """降级方案：从 learning_record 推断薄弱知识点"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock()

    row1 = MagicMock()
    row1.knowledge_point_name = "方程"; row1.avg_acc = 45.0
    row2 = MagicMock()
    row2.knowledge_point_name = "几何"; row2.avg_acc = 55.0

    rows_result = MagicMock()
    rows_result.all.return_value = [row1, row2]
    session.execute.return_value = rows_result

    _patch_session(monkeypatch, "backend.services.record_service", session)

    items = await svc._fallback_low_mastery(user_id=7)

    assert len(items) >= 1
    assert items[0]["type"] == "practice"


@pytest.mark.asyncio
async def test_review_due_recommendation_handles_missing_tables(monkeypatch):
    """跨模块表不存在时不抛出异常"""
    from backend.services.record_service import RecordService

    svc = RecordService()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=Exception("Table doesn't exist"))

    _patch_session(monkeypatch, "backend.services.record_service", session)

    result = await svc._get_review_due_recommendation(user_id=7, today=date(2026, 7, 22))
    assert result is None


# ============================================================
# 测试 10：数据模型
# ============================================================

def test_learning_record_model_fields():
    from backend.model.learning_models import LearningRecord
    assert LearningRecord.__tablename__ == 'learning_record'
    assert hasattr(LearningRecord, 'user_id')
    assert hasattr(LearningRecord, 'record_type')
    assert hasattr(LearningRecord, 'request_id')


def test_notification_model_fields():
    from backend.model.learning_models import Notification
    assert Notification.__tablename__ == 'notification'
    assert hasattr(Notification, 'is_read')
    assert hasattr(Notification, 'type')


def test_learning_report_model_fields():
    from backend.model.learning_models import LearningReport
    assert LearningReport.__tablename__ == 'learning_report'
    assert hasattr(LearningReport, 'date_from')
    assert hasattr(LearningReport, 'date_to')
    assert hasattr(LearningReport, 'weak_points')


def test_cross_module_models_exist():
    from backend.model.cross_module_models import Mistake, ReviewPlan, KnowledgeMastery
    assert Mistake.__tablename__ == 'mistake'
    assert ReviewPlan.__tablename__ == 'review_plan'
    assert KnowledgeMastery.__tablename__ == 'knowledge_mastery'
