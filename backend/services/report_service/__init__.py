"""成员四：学情报告生成 Service"""

import uuid
from datetime import date, datetime
from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger
from backend.model import AsyncSessionLocal
from backend.model.learning_models import LearningRecord, LearningReport

logger = get_logger(__name__)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _now() -> datetime:
    return datetime.now(SHANGHAI)


class ReportService:
    """阶段性学情报告服务"""

    async def generate_report(
        self,
        user_id: int,
        date_from: str,
        date_to: str,
        request_id: str,
    ) -> Dict:
        """
        生成阶段性学情报告。

        统计范围：[date_from, date_to]，基于 learning_record 汇总。
        跨模块数据（错因）尝试从 mistake 表获取，降级使用空值。
        """
        # ── 幂等检查（先查是否已存在） ──
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(LearningReport).where(LearningReport.request_id == request_id)
            )
            existing_report = existing.scalar_one_or_none()
            if existing_report:
                return self._report_to_dict(existing_report)

        # ── 统计数据 ──
        stats = await self._gather_stats(user_id, date_from, date_to)

        # ── 高频错因（跨模块） ──
        frequent_error = await self._get_frequent_error(user_id, date_from, date_to)

        # ── 薄弱知识点 ──
        weak_points = await self._get_weak_points(user_id, date_from, date_to)

        # ── 生成建议 ──
        suggestion = self._generate_suggestion(stats, frequent_error, weak_points)

        # ── 持久化 ──
        async with AsyncSessionLocal() as session:

            report = LearningReport(
                user_id=user_id,
                date_from=date.fromisoformat(date_from),
                date_to=date.fromisoformat(date_to),
                practice_count=stats["practice_count"],
                question_count=stats["question_count"],
                accuracy=stats["accuracy"],
                mastery_change=stats["mastery_change"],
                frequent_error_type=frequent_error,
                weak_points=weak_points,
                suggestion=suggestion,
                request_id=request_id,
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
            logger.info("Generated report %s for user %s", report.id, user_id)
            return self._report_to_dict(report)

    async def get_reports(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict], int, int]:
        """分页查询历史报告"""
        async with AsyncSessionLocal() as session:
            conditions = [LearningReport.user_id == user_id]
            count_q = select(func.count()).select_from(LearningReport).where(and_(*conditions))
            total = (await session.execute(count_q)).scalar() or 0

            offset = (page - 1) * page_size
            q = (
                select(LearningReport)
                .where(and_(*conditions))
                .order_by(LearningReport.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            rows = (await session.execute(q)).scalars().all()

            items = [
                {
                    "report_id": r.id,
                    "date_from": r.date_from.isoformat() if r.date_from else "",
                    "date_to": r.date_to.isoformat() if r.date_to else "",
                    "practice_count": r.practice_count,
                    "accuracy": float(r.accuracy) if r.accuracy is not None else None,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
            pages = ceil(total / page_size) if total else 0
            return items, total, pages

    async def get_report_detail(self, user_id: int, report_id: int) -> Dict:
        """查询单份报告详情，校验归属"""
        async with AsyncSessionLocal() as session:
            q = select(LearningReport).where(
                and_(LearningReport.id == report_id, LearningReport.user_id == user_id)
            )
            report = (await session.execute(q)).scalar_one_or_none()
            if not report:
                raise BusinessError("REPORT_NOT_FOUND", "报告不存在", 404)
            return self._report_to_dict(report)

    # ─── 内部统计方法 ─────────────────────────────────

    async def _gather_stats(
        self, user_id: int, date_from: str, date_to: str
    ) -> Dict:
        """从 learning_record 汇总统计数据"""
        async with AsyncSessionLocal() as session:
            q = select(
                func.count().label('practice_cnt'),
                func.sum(LearningRecord.question_count).label('question_cnt'),
                func.avg(LearningRecord.accuracy).label('avg_acc'),
                func.sum(LearningRecord.mastery_change).label('total_mastery_change'),
            ).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.record_type.in_(['practice', 'correction']),
                    LearningRecord.occurred_at >= f"{date_from} 00:00:00",
                    LearningRecord.occurred_at <= f"{date_to} 23:59:59",
                )
            )
            row = (await session.execute(q)).fetchone()

            return {
                "practice_count": row.practice_cnt or 0,
                "question_count": row.question_cnt or 0,
                "accuracy": round(float(row.avg_acc), 2) if row.avg_acc else 0.0,
                "mastery_change": row.total_mastery_change or 0,
            }

    async def _get_frequent_error(
        self, user_id: int, date_from: str, date_to: str
    ) -> Optional[str]:
        """尝试从 mistake 表获取高频错因"""
        try:
            async with AsyncSessionLocal() as session:
                sql = text(
                    """
                    SELECT error_type, COUNT(*) as cnt
                    FROM mistake
                    WHERE user_id = :uid
                      AND created_at >= :date_from
                      AND created_at <= :date_to_end
                    GROUP BY error_type
                    ORDER BY cnt DESC
                    LIMIT 1
                    """
                )
                result = await session.execute(sql, {
                    "uid": user_id,
                    "date_from": f"{date_from} 00:00:00",
                    "date_to_end": f"{date_to} 23:59:59",
                })
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning("Frequent error query failed: %s", e)
            return None

    async def _get_weak_points(
        self, user_id: int, date_from: str, date_to: str
    ) -> List[str]:
        """从 learning_record 中找出正确率低的知识点"""
        async with AsyncSessionLocal() as session:
            q = (
                select(
                    LearningRecord.knowledge_point_name,
                    func.avg(LearningRecord.accuracy).label('avg_acc'),
                    func.count().label('cnt'),
                )
                .where(
                    and_(
                        LearningRecord.user_id == user_id,
                        LearningRecord.knowledge_point_name.isnot(None),
                        LearningRecord.accuracy.isnot(None),
                        LearningRecord.occurred_at >= f"{date_from} 00:00:00",
                        LearningRecord.occurred_at <= f"{date_to} 23:59:59",
                    )
                )
                .group_by(LearningRecord.knowledge_point_name)
                .having(func.avg(LearningRecord.accuracy) < 70)
                .order_by(func.avg(LearningRecord.accuracy))
                .limit(3)
            )
            rows = (await session.execute(q)).all()
            return [row.knowledge_point_name for row in rows if row.knowledge_point_name]

    def _generate_suggestion(
        self,
        stats: Dict,
        frequent_error: Optional[str],
        weak_points: List[str],
    ) -> str:
        """根据统计数据生成简短建议"""
        parts = []

        if stats["accuracy"] < 60:
            parts.append("当前正确率偏低")
        elif stats["accuracy"] >= 80:
            parts.append("正确率表现良好")

        error_map = {
            "knowledge": "建议重点回顾相关概念和公式",
            "calculation": "建议加强计算基本功",
            "reading": "建议练习审题能力",
            "method": "建议梳理常见解题方法",
        }
        if frequent_error and frequent_error in error_map:
            parts.append(error_map[frequent_error])

        if weak_points:
            parts.append(f"优先复习：{'、'.join(weak_points[:2])}")

        if not parts:
            parts.append("保持当前学习节奏")

        return "；".join(parts)

    def _report_to_dict(self, r: LearningReport) -> Dict:
        """ORM → 响应字典"""
        return {
            "report_id": r.id,
            "date_from": r.date_from.isoformat() if r.date_from else "",
            "date_to": r.date_to.isoformat() if r.date_to else "",
            "practice_count": r.practice_count,
            "question_count": r.question_count,
            "accuracy": float(r.accuracy) if r.accuracy is not None else 0.0,
            "mastery_change": r.mastery_change,
            "frequent_error_type": r.frequent_error_type,
            "weak_points": r.weak_points if r.weak_points else [],
            "suggestion": r.suggestion,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }


# 全局单例
report_service = ReportService()
