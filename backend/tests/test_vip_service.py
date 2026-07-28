from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.exceptions import BusinessError
from backend.services.vip_service.vip_service import VipService


class StubVipMapper:
    def __init__(self, vip_info=None, counts=None, existing=None):
        self.vip_info = vip_info
        self.counts = counts or {}
        self.existing = existing
        self.added = []
        self.locked = False

    async def lock_user(self, _db, _user_id):
        self.locked = True

    async def get_vip_info(self, _db, _user_id):
        return self.vip_info

    async def get_usage_by_request_id(self, _db, _request_id):
        return self.existing

    async def count_usage(
        self,
        _db,
        _user_id,
        _usage_date,
        feature,
        *,
        usage_source=None,
    ):
        return self.counts.get((feature, usage_source), self.counts.get(feature, 0))

    def add_usage(self, _db, usage):
        self.added.append(usage)


def make_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_expired_vip_uses_normal_daily_limit():
    now = datetime(2026, 7, 22, 12, 0)
    info = SimpleNamespace(started_at=now - timedelta(days=31), expires_at=now - timedelta(days=1))
    mapper = StubVipMapper(vip_info=info, counts={("practice_generation", "quota"): 4})

    result = await VipService(mapper).check_entitlement(
        make_db(), user_id=7, feature="practice_generation", now=now
    )

    assert result == {"allowed": True, "membership": "normal", "remaining": 1}


@pytest.mark.asyncio
async def test_normal_user_sixth_practice_is_rejected():
    mapper = StubVipMapper(counts={("practice_generation", "quota"): 5})

    with pytest.raises(BusinessError) as exc_info:
        await VipService(mapper).check_entitlement(
            make_db(),
            user_id=7,
            feature="practice_generation",
            now=datetime(2026, 7, 22, 12, 0),
        )

    assert exc_info.value.code == "USAGE_LIMIT_REACHED"


@pytest.mark.asyncio
async def test_active_vip_has_twenty_practice_limit():
    now = datetime(2026, 7, 22, 12, 0)
    info = SimpleNamespace(started_at=now, expires_at=now + timedelta(days=30))
    mapper = StubVipMapper(vip_info=info, counts={("practice_generation", "quota"): 19})

    result = await VipService(mapper).get_usage(make_db(), user_id=7, now=now)

    assert result["membership"] == "vip"
    assert result["practice_generation"] == {"used": 19, "limit": 20, "remaining": 1}
    assert result["stage_report"]["limit"] is None


@pytest.mark.asyncio
async def test_consume_usage_is_idempotent():
    existing = SimpleNamespace(user_id=7)
    mapper = StubVipMapper(existing=existing)
    db = make_db()

    result = await VipService(mapper).consume_usage(
        db,
        user_id=7,
        feature="practice_generation",
        request_id="generation-1",
        now=datetime(2026, 7, 22, 12, 0),
    )

    assert result == {"consumed": False, "reason": "duplicate"}
    assert mapper.added == []
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_usage_records_only_after_confirmation():
    mapper = StubVipMapper(counts={("practice_generation", "quota"): 2})
    db = make_db()

    result = await VipService(mapper).consume_usage(
        db,
        user_id=7,
        feature="practice_generation",
        request_id="generation-2",
        now=datetime(2026, 7, 22, 12, 0),
    )

    assert mapper.locked is True
    assert mapper.added[0].usage_date == date(2026, 7, 22)
    assert result["remaining"] == 2
    db.commit.assert_awaited_once()
