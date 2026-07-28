from datetime import date
from unittest.mock import AsyncMock

import pytest

from backend.services.mastery_service.mastery_service import MasteryService


@pytest.mark.asyncio
async def test_mastery_trend_serializes_database_date():
    """MySQL DATE() values must be serialized to the response schema's string."""
    mapper = AsyncMock()
    mapper.get_mastery_trend_days.return_value = [
        (date(2026, 7, 25), 57),
        (date(2026, 7, 26), 63),
    ]

    result = await MasteryService(mapper).get_mastery_trend(user_id=1, days=7)

    assert [point.date for point in result.points] == ["2026-07-25", "2026-07-26"]
    assert result.current_score == 63
    assert result.change == 6
