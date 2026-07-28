from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.api.mastery_api.mastery_api import get_mistake_analysis
from backend.schemas.request.mastery_request import MistakeAnalysisRequest
from backend.schemas.response.mastery_response import MistakeAnalysisResponse


@pytest.mark.asyncio
async def test_basic_mistake_analysis_hides_detail_without_authorization():
    service = AsyncMock()
    service.get_mistake_analysis.return_value = MistakeAnalysisResponse(
        mistake_id=3,
        standard_answer="42",
        simple_analysis="先列出等式。",
        detailed_analysis="完整推导过程。",
    )
    result = await get_mistake_analysis(
        mistake_id=3,
        req=MistakeAnalysisRequest(payment_method="basic"),
        user=SimpleNamespace(id=9),
        db=AsyncMock(),
        service=service,
        x_request_id="basic-analysis-1",
    )

    assert result["data"]["standard_answer"] == "42"
    assert result["data"]["simple_analysis"] == "先列出等式。"
    assert result["data"]["detailed_analysis"] is None
    assert result["data"]["payment_method"] == "basic"
