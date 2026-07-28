from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.model.point_account import PointAccount
from backend.services.point_service.point_service import PointService
from backend.tests.test_point_service import StubPointMapper, make_db


@pytest.mark.asyncio
async def test_valid_practice_rewards_five_points():
    account = PointAccount(user_id=7, balance=0, earned_total=0, spent_total=0)
    mapper = StubPointMapper(account=account)
    event = SimpleNamespace(
        user_id=7,
        request_id="practice-reward-1",
        occurred_at=datetime(2026, 7, 22, 10, 0),
        practice_id=101,
        is_valid=True,
    )

    result = await PointService(mapper).reward_practice(make_db(), event)

    assert result["awarded"] is True
    assert result["points"] == 5
    assert account.balance == 5
    assert mapper.added_transactions[0].business_id == "101"


@pytest.mark.asyncio
async def test_invalid_practice_does_not_reward():
    mapper = StubPointMapper()
    event = SimpleNamespace(
        user_id=7,
        request_id="practice-reward-2",
        occurred_at=datetime(2026, 7, 22, 10, 0),
        practice_id=102,
        is_valid=False,
    )

    result = await PointService(mapper).reward_practice(make_db(), event)

    assert result == {"awarded": False, "reason": "invalid_practice", "points": 0}
    assert mapper.added_transactions == []


@pytest.mark.asyncio
async def test_daily_practice_reward_stops_after_three_groups():
    account = PointAccount(user_id=7, balance=15, earned_total=15, spent_total=0)
    mapper = StubPointMapper(account=account, counts={"practice_reward": 3})
    db = make_db()
    event = SimpleNamespace(
        user_id=7,
        request_id="practice-reward-4",
        occurred_at=datetime(2026, 7, 22, 11, 0),
        practice_id=104,
        is_valid=True,
    )

    result = await PointService(mapper).reward_practice(db, event)

    assert result == {"awarded": False, "reason": "limit_reached", "points": 0}
    assert account.balance == 15
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_tasks_report_daily_progress_and_claim_state():
    mapper = StubPointMapper(
        counts={
            "daily_check_in": 1,
            "practice_reward": 2,
            "correction_reward": 0,
            "streak_3_days": 1,
        }
    )

    result = await PointService(mapper).get_tasks(
        make_db(),
        user_id=7,
        now=datetime(2026, 7, 22, 12, 0),
    )

    assert result["date"].isoformat() == "2026-07-22"
    assert [item["claimed"] for item in result["items"]] == [True, False, False, True]
    assert result["items"][1]["progress"] == 2


@pytest.mark.asyncio
async def test_failed_or_repeated_correction_does_not_reward():
    mapper = StubPointMapper()
    event = SimpleNamespace(
        user_id=7,
        request_id="correction-reward-1",
        occurred_at=datetime(2026, 7, 22, 12, 0),
        mistake_id=301,
        first_success=False,
    )

    result = await PointService(mapper).reward_correction(make_db(), event)

    assert result == {"awarded": False, "reason": "not_first_success", "points": 0}
    assert mapper.added_transactions == []


@pytest.mark.asyncio
async def test_daily_check_in_rewards_two_points():
    account = PointAccount(user_id=7, balance=10, earned_total=10, spent_total=0)
    mapper = StubPointMapper(account=account)

    result = await PointService(mapper).check_in(
        make_db(),
        user_id=7,
        request_id="check-in-1",
        occurred_at=datetime(2026, 7, 22, 8, 0),
    )

    assert result["awarded"] is True
    assert result["points"] == 2
    assert result["balance"] == 12
    assert mapper.added_transactions[0].business_type == "daily_check_in"


@pytest.mark.asyncio
async def test_second_check_in_on_same_day_does_not_reward():
    account = PointAccount(user_id=7, balance=12, earned_total=12, spent_total=0)
    mapper = StubPointMapper(account=account, counts={"daily_check_in": 1})

    result = await PointService(mapper).check_in(
        make_db(),
        user_id=7,
        request_id="check-in-2",
        occurred_at=datetime(2026, 7, 22, 9, 0),
    )

    assert result == {"awarded": False, "reason": "limit_reached", "points": 0}
    assert account.balance == 12


@pytest.mark.asyncio
async def test_three_consecutive_learning_days_reward_streak():
    account = PointAccount(user_id=7, balance=0, earned_total=0, spent_total=0)
    mapper = StubPointMapper(
        account=account,
        learning_times=[
            datetime(2026, 7, 22, 10, 0),
            datetime(2026, 7, 21, 10, 0),
            datetime(2026, 7, 20, 10, 0),
        ],
    )

    result = await PointService(mapper).reward_streak_if_eligible(
        make_db(), user_id=7, occurred_at=datetime(2026, 7, 22, 12, 0)
    )

    assert result["awarded"] is True
    assert result["points"] == 10
    assert mapper.added_transactions[0].request_id == "streak:7:2026-07-20:1"


@pytest.mark.asyncio
async def test_non_consecutive_learning_days_do_not_reward_streak():
    mapper = StubPointMapper(
        learning_times=[
            datetime(2026, 7, 22, 10, 0),
            datetime(2026, 7, 20, 10, 0),
            datetime(2026, 7, 19, 10, 0),
        ],
    )

    result = await PointService(mapper).reward_streak_if_eligible(
        make_db(), user_id=7, occurred_at=datetime(2026, 7, 22, 12, 0)
    )

    assert result == {"awarded": False, "reason": "streak_not_reached", "points": 0}
