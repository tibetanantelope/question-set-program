from unittest.mock import AsyncMock

import pytest

from backend.services.knowledge_review_service import (
    _card_for_mode,
    _card_for_mode_with_ai,
    _parse_generated_card,
)


def _generated_card_text(content: str) -> str:
    return (
        '{'
        f'"summary":"{content}",'
        '"concepts":["概念一","概念二","概念三"],'
        '"formula":"核心结构",'
        '"pitfalls":["易错一","易错二","易错三"],'
        '"example":{"question":"例题","answer":"答案",'
        '"steps":["步骤一","步骤二"]},'
        '"quiz":['
        '{"question":"题一","options":["选项一","选项二","选项三"],'
        '"correct_index":0,"explanation":"依据一"},'
        '{"question":"题二","options":["选项一","选项二","选项三"],'
        '"correct_index":1,"explanation":"依据二"},'
        '{"question":"题三","options":["选项一","选项二","选项三"],'
        '"correct_index":2,"explanation":"依据三"}],'
        '"advanced_focus":"迁移目标"'
        '}'
    )


def test_parser_accepts_relevant_chinese_compound_name_without_exact_repetition():
    raw = _generated_card_text("说明作对现在的影响，并分析现在的影响。").replace(
        "作对现在的影响，并分析现在的影响。", "作对现在的影响，并分析现在的影响。"
    )

    card = _parse_generated_card(raw, "作对现在的影响", "full")

    assert card["summary"].startswith("说明作对现在的影响")


@pytest.mark.asyncio
async def test_dynamic_card_uses_mode_appropriate_fallback_when_ai_fails(monkeypatch):
    failure = AsyncMock(side_effect=ValueError("generated card is not relevant enough"))
    monkeypatch.setattr(
        "backend.services.knowledge_review_service._generate_dynamic_card", failure
    )

    card = await _card_for_mode_with_ai("陌生知识点", "计算机", "quick")

    assert card["quiz"] == _card_for_mode("陌生知识点", "quick")["quiz"]
    assert len(card["quiz"]) == 2
    failure.assert_awaited_once()
