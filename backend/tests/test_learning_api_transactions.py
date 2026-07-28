from unittest.mock import AsyncMock

import pytest

from backend.schemas.request.learning_request import AnswerSubmitRequest
from backend.schemas.response.learning_response import (
    AnswerResultItem,
    AnswerSubmitResponse,
    PracticeResponse,
    QuestionItem,
)


class ExpiringUser:
    """Simulate an ORM user whose attributes expire after a transaction."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.reads = 0

    @property
    def id(self) -> int:
        self.reads += 1
        if self.reads > 1:
            raise AssertionError("user.id was read again after a transaction boundary")
        return self.user_id


@pytest.mark.asyncio
async def test_submit_answers_keeps_scalar_user_id_across_commits(monkeypatch):
    from backend.api.learning_api import learning_api

    service = AsyncMock()
    service.submit_answers.return_value = AnswerSubmitResponse(
        practice_id=19,
        status="completed",
        question_count=1,
        correct_count=1,
        accuracy=100,
        current_difficulty="easy",
        next_difficulty="medium",
        results=[
            AnswerResultItem(
                question_id=1,
                is_correct=True,
                standard_answer="done",
                analysis="ok",
            )
        ],
    )
    service.get_practice.return_value = PracticeResponse(
        practice_id=19,
        knowledge_point_name="现在完成时",
        difficulty="easy",
        status="completed",
        questions=[
            QuestionItem(
                question_id=1,
                content="Complete the sentence.",
                knowledge_point_name="现在完成时",
            )
        ],
    )

    mastery_service = AsyncMock()
    monkeypatch.setattr(
        learning_api,
        "get_mastery_service",
        AsyncMock(return_value=mastery_service),
    )
    monkeypatch.setattr(learning_api.record_service, "record_practice", AsyncMock())
    monkeypatch.setattr(learning_api.record_service, "update_plan_progress", AsyncMock())
    monkeypatch.setattr(learning_api.point_service, "reward_practice", AsyncMock())
    monkeypatch.setattr(
        learning_api.point_service,
        "reward_streak_if_eligible",
        AsyncMock(),
    )

    user = ExpiringUser(1)
    response = await learning_api.submit_answers(
        practice_id=19,
        req=AnswerSubmitRequest(answers=[{"question_id": 1, "answer": "done"}]),
        user=user,
        db=AsyncMock(),
        service=service,
        x_request_id="answer-submit-transaction-test",
    )

    assert response["code"] == "OK"
    assert user.reads == 1
