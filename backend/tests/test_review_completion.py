from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.core.exceptions import BusinessError
from backend.schemas.request.mastery_request import CorrectionSubmitRequest
from backend.services.mastery_service.mastery_service import MasteryService


def make_mapper(*, valid_review: bool):
    mistake = SimpleNamespace(
        id=41,
        standard_answer="x=6",
        first_correction_success=True,
        correction_correct=True,
        correction_status="corrected",
        knowledge_point_id=7,
        knowledge_point_name="一元一次方程",
        subject="数学",
    )
    mapper = SimpleNamespace(
        get_mistake_by_correction_request=AsyncMock(return_value=None),
        get_mistake=AsyncMock(return_value=mistake),
        has_pending_review=AsyncMock(return_value=valid_review),
        update_mistake_correction=AsyncMock(return_value=mistake),
        complete_review=AsyncMock(return_value=True),
        get_mastery=AsyncMock(return_value=None),
    )
    return mapper


@pytest.mark.asyncio
async def test_correct_review_answer_marks_owned_plan_completed():
    mapper = make_mapper(valid_review=True)
    service = MasteryService(mapper)

    result = await service.submit_correction(
        user_id=9,
        mistake_id=41,
        req=CorrectionSubmitRequest(answer="x=6", review_id=88),
        request_id="review-complete-88",
    )

    assert result.is_correct is True
    mapper.has_pending_review.assert_awaited_once_with(88, 9, 41)
    mapper.complete_review.assert_awaited_once_with(88, 9, 41)


@pytest.mark.asyncio
async def test_reveal_finishes_current_round_and_reduces_mastery():
    mistake = SimpleNamespace(
        id=41,
        standard_answer="x=6",
        knowledge_point_id=7,
        knowledge_point_name="一元一次方程",
    )
    mastery = SimpleNamespace(id=12, mastery_score=64)
    mapper = SimpleNamespace(
        reveal_review=AsyncMock(return_value=(
            SimpleNamespace(id=88), mistake, "移项后两边同时除以系数。"
        )),
        get_mastery=AsyncMock(return_value=mastery),
        update_mastery=AsyncMock(),
        get_review_progress=AsyncMock(return_value=(1, 3, __import__('datetime').date(2026, 7, 30))),
    )
    service = MasteryService(mapper)

    result = await service.reveal_review_answer(9, 41, 88)

    assert result.standard_answer == "x=6"
    assert result.mastery_change == -2
    assert result.mastery_after == 62
    assert result.current_round == 1
    assert result.total_rounds == 3
    assert result.next_review_date == "2026-07-30"
    mapper.update_mastery.assert_awaited_once_with(12, -2, False, "consolidating")


@pytest.mark.asyncio
async def test_cannot_complete_review_owned_by_another_user():
    mapper = make_mapper(valid_review=False)
    service = MasteryService(mapper)

    with pytest.raises(BusinessError) as exc:
        await service.submit_correction(
            user_id=9,
            mistake_id=41,
            req=CorrectionSubmitRequest(answer="x=6", review_id=99),
            request_id="review-forbidden-99",
        )

    assert exc.value.code == "REVIEW_NOT_FOUND"
    mapper.update_mistake_correction.assert_not_awaited()
    mapper.complete_review.assert_not_awaited()
