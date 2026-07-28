from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.exceptions import BusinessError
from backend.schemas.request.record_request import GenerateReportRequest
from backend.services.learning_service.learning_service import LearningService
from backend.services.vip_service.vip_service import VipService


@pytest.mark.asyncio
async def test_detailed_analysis_requires_owned_completed_practice():
    mapper = SimpleNamespace(get_practice=AsyncMock(return_value=None))
    service = LearningService(mapper=mapper)

    with pytest.raises(BusinessError) as exc:
        await service.get_detailed_analysis(user_id=8, practice_id=99)

    assert exc.value.code == "PRACTICE_NOT_FOUND"
    mapper.get_practice.assert_awaited_once_with(99, 8)


@pytest.mark.asyncio
async def test_detailed_analysis_returns_only_wrong_question_details():
    practice = SimpleNamespace(status="completed")
    questions = [
        SimpleNamespace(
            id=1, is_correct=True, error_type=None,
            error_description=None, next_suggestion=None,
        ),
        SimpleNamespace(
            id=2, is_correct=False, error_type="calculation",
            error_description="移项后符号未改变", next_suggestion="再练两道移项题",
        ),
    ]
    mapper = SimpleNamespace(
        get_practice=AsyncMock(return_value=practice),
        get_questions=AsyncMock(return_value=questions),
    )

    result = await LearningService(mapper=mapper).get_detailed_analysis(8, 21)

    assert result == [{
        "question_id": 2,
        "error_type": "calculation",
        "error_description": "移项后符号未改变",
        "next_suggestion": "再练两道移项题",
    }]


class FeatureMapper:
    def __init__(self):
        self.added = []

    async def get_vip_info(self, _db, _user_id):
        return None

    async def get_usage_by_request_id(self, _db, _request_id):
        return None

    def add_usage(self, _db, usage):
        self.added.append(usage)


@pytest.mark.asyncio
async def test_point_feature_authorization_deducts_and_records_usage():
    mapper = FeatureMapper()
    points = SimpleNamespace(exchange=AsyncMock(return_value={"balance": 30}))
    db = AsyncMock()
    db.add = MagicMock()
    service = VipService(mapper=mapper, points=points)

    result = await service.authorize_feature(
        db,
        user_id=8,
        feature="detailed_analysis",
        payment_method="points",
        request_id="detail-21",
        now=datetime(2026, 7, 25, 12, 0),
    )

    assert result == {"allowed": True, "payment_method": "points"}
    points.exchange.assert_awaited_once()
    assert mapper.added[0].feature == "detailed_analysis"
    assert mapper.added[0].usage_source == "points"
    db.commit.assert_awaited_once()


def test_report_rejects_invalid_range_before_entitlement_processing():
    with pytest.raises(ValueError):
        GenerateReportRequest(
            date_from="2026-07-25",
            date_to="2026-07-01",
            payment_method="points",
        )
