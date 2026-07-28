"""按真实答题记录重算知识点掌握度。

运行方式：
    python -m backend.scripts.recalculate_mastery_scores

无答题证据的知识点保留内部中性值 50，接口层应显示“待评估”，不把它
误解为用户已掌握 50%。有证据时按题目难度和历史证据量逐题更新。
"""

import asyncio

from sqlalchemy import and_, or_, select, text

from backend.model import AsyncSessionLocal, engine
from backend.model.mastery import AnswerRecord, KnowledgeMastery
from backend.services.mastery_service.mastery_service import (
    _score_to_status,
    calculate_mastery_after_answer,
)


async def recalculate() -> tuple[int, int]:
    updated = 0
    without_evidence = 0

    async with AsyncSessionLocal() as session:
        if session.bind and session.bind.dialect.name == "mysql":
            await session.execute(
                text(
                    "ALTER TABLE knowledge_mastery "
                    "MODIFY COLUMN mastery_score INT NOT NULL DEFAULT 50 "
                    "COMMENT '掌握度内部估计: 0-100；无证据时显示待评估', "
                    "MODIFY COLUMN learning_status VARCHAR(32) NOT NULL DEFAULT 'weak' "
                    "COMMENT 'weak/consolidating/mastered'"
                )
            )
        masteries = (
            await session.execute(
                select(KnowledgeMastery).order_by(KnowledgeMastery.id)
            )
        ).scalars().all()

        for mastery in masteries:
            identity_filter = AnswerRecord.knowledge_point_id == mastery.knowledge_point_id
            if not mastery.knowledge_point_id:
                identity_filter = or_(
                    AnswerRecord.knowledge_point_id.is_(None),
                    AnswerRecord.knowledge_point_id == 0,
                )

            records = (
                await session.execute(
                    select(AnswerRecord)
                    .where(
                        and_(
                            AnswerRecord.user_id == mastery.user_id,
                            identity_filter,
                        )
                    )
                    .order_by(AnswerRecord.created_at, AnswerRecord.id)
                )
            ).scalars().all()

            # 兼容早期未正确写入 knowledge_point_id 的历史记录，但严格限制
            # 在同一用户和同名知识点内，避免跨知识点混算。
            if not records and mastery.knowledge_point_name:
                records = (
                    await session.execute(
                        select(AnswerRecord)
                        .where(
                            AnswerRecord.user_id == mastery.user_id,
                            AnswerRecord.knowledge_point_name == mastery.knowledge_point_name,
                        )
                        .order_by(AnswerRecord.created_at, AnswerRecord.id)
                    )
                ).scalars().all()

            score = 50
            correct_count = 0
            for count, record in enumerate(records):
                score = calculate_mastery_after_answer(
                    score,
                    count,
                    bool(record.is_correct),
                    record.difficulty or "medium",
                )
                correct_count += int(bool(record.is_correct))

            mastery.mastery_score = score
            mastery.learning_status = _score_to_status(score)
            mastery.answer_count = len(records)
            mastery.correct_count = correct_count
            mastery.last_studied_at = records[-1].created_at if records else None
            updated += 1
            without_evidence += int(not records)

        await session.commit()

    await engine.dispose()
    return updated, without_evidence


if __name__ == "__main__":
    changed, empty = asyncio.run(recalculate())
    print(f"Recalculated {changed} mastery rows; {empty} rows have no answer evidence.")
