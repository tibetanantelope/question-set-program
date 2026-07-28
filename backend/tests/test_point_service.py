from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from backend.core.exceptions import BusinessError
from backend.model.point_account import PointAccount
from backend.services.point_service.point_service import PointService


class StubPointMapper:
    def __init__(self, account=None, transaction=None, counts=None, learning_times=None):
        self.account = account
        self.transaction = transaction
        self.counts = counts or {}
        self.learning_times = learning_times or []
        self.added_transactions = []

    async def get_account(self, _db, _user_id, *, for_update=False):
        return self.account

    async def get_or_create_account(self, _db, user_id, *, for_update=False):
        if self.account is None:
            self.account = PointAccount(
                user_id=user_id,
                balance=0,
                earned_total=0,
                spent_total=0,
            )
        return self.account

    async def get_transaction_by_request_id(self, _db, _request_id):
        return self.transaction

    async def count_transactions(
        self,
        _db,
        _user_id,
        business_type,
        *,
        started_at=None,
        ended_at=None,
        business_id=None,
    ):
        return self.counts.get((business_type, business_id), self.counts.get(business_type, 0))

    async def count_transactions_by_type(
        self, _db, _user_id, *, started_at, ended_at
    ):
        return {
            key: value
            for key, value in self.counts.items()
            if isinstance(key, str)
        }

    async def list_transactions(self, _db, _user_id, _page, _page_size):
        return self.added_transactions, len(self.added_transactions)

    async def list_recent_learning_times(self, _db, _user_id, *, limit=400):
        return self.learning_times[:limit]

    def add_transaction(self, _db, transaction):
        self.added_transactions.append(transaction)


def make_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_streak_task_uses_days_over_three_target_and_caps_progress():
    now = datetime(2026, 7, 27, 12, tzinfo=ZoneInfo("Asia/Shanghai"))
    mapper = StubPointMapper(
        learning_times=[now - timedelta(days=offset) for offset in range(5)]
    )

    result = await PointService(mapper).get_tasks(make_db(), user_id=7, now=now)

    streak = next(item for item in result["items"] if item["task_type"] == "streak_3_days")
    assert streak["progress"] == 3
    assert streak["target"] == 3
    assert streak["claimed"] is True


@pytest.mark.asyncio
async def test_get_account_creates_zero_balance_account():
    mapper = StubPointMapper()
    db = make_db()

    result = await PointService(mapper).get_account(db, user_id=7)

    assert result == {"balance": 0, "earned_total": 0, "spent_total": 0}
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_points_rewards_and_writes_transaction():
    account = PointAccount(user_id=7, balance=10, earned_total=10, spent_total=0)
    mapper = StubPointMapper(account=account)
    db = make_db()

    result = await PointService(mapper).change_points(
        db,
        user_id=7,
        amount=5,
        business_type="practice_reward",
        description="完成有效练习",
        request_id="practice-001",
    )

    assert result == {"balance": 15, "earned_total": 15, "spent_total": 0}
    assert len(mapper.added_transactions) == 1
    assert mapper.added_transactions[0].balance_after == 15
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_request_id_is_idempotent():
    account = PointAccount(user_id=7, balance=15, earned_total=15, spent_total=0)
    existing = SimpleNamespace(user_id=7)
    mapper = StubPointMapper(account=account, transaction=existing)
    db = make_db()

    result = await PointService(mapper).change_points(
        db,
        user_id=7,
        amount=5,
        business_type="practice_reward",
        description="完成有效练习",
        request_id="practice-001",
    )

    assert result["balance"] == 15
    assert mapper.added_transactions == []
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_deducts_configured_cost():
    account = PointAccount(user_id=7, balance=30, earned_total=30, spent_total=0)
    mapper = StubPointMapper(account=account)
    db = make_db()

    result = await PointService(mapper).exchange(
        db,
        user_id=7,
        item_type="stage_report",
        target_id=12,
        request_id="exchange-001",
    )

    assert result == {
        "item_type": "stage_report",
        "target_id": 12,
        "cost": 20,
        "balance": 10,
    }
    assert account.spent_total == 20


@pytest.mark.asyncio
async def test_exchange_rejects_insufficient_points_without_commit():
    account = PointAccount(user_id=7, balance=5, earned_total=5, spent_total=0)
    mapper = StubPointMapper(account=account)
    db = make_db()

    with pytest.raises(BusinessError) as exc_info:
        await PointService(mapper).exchange(
            db,
            user_id=7,
            item_type="extra_practice",
            target_id=None,
            request_id="exchange-002",
        )

    assert exc_info.value.code == "INSUFFICIENT_POINTS"
    assert account.balance == 5
    assert mapper.added_transactions == []
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_id_cannot_be_reused_by_another_user():
    account = PointAccount(user_id=8, balance=10, earned_total=10, spent_total=0)
    existing = SimpleNamespace(user_id=7)
    mapper = StubPointMapper(account=account, transaction=existing)
    db = make_db()

    with pytest.raises(BusinessError) as exc_info:
        await PointService(mapper).change_points(
            db,
            user_id=8,
            amount=5,
            business_type="practice_reward",
            description="完成有效练习",
            request_id="practice-001",
        )

    assert exc_info.value.code == "REQUEST_ID_CONFLICT"
    assert mapper.added_transactions == []
