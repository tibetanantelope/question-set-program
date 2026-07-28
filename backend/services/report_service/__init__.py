"""成员四：学情报告生成 Service"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger
from backend.model import AsyncSessionLocal
from backend.model.learning_models import LearningRecord, LearningReport
from backend.model.user_profile import UserProfile
from backend.model.mastery import KnowledgeReviewRecord

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
                data = self._report_to_dict(existing_report)
                await self._add_detailed_analysis(data, user_id, date_from, date_to)
                return data

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
            data = self._report_to_dict(report)
            await self._add_detailed_analysis(data, user_id, date_from, date_to)
            return data

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
            data = self._report_to_dict(report)
            await self._add_detailed_analysis(
                data, user_id, report.date_from.isoformat(), report.date_to.isoformat()
            )
            return data

    # ─── 内部统计方法 ─────────────────────────────────

    async def _gather_stats(
        self, user_id: int, date_from: str, date_to: str, subject: Optional[str] = None
    ) -> Dict:
        """从 learning_record 汇总统计数据"""
        async with AsyncSessionLocal() as session:
            q = select(
                func.sum(
                    func.if_(LearningRecord.record_type == 'practice', 1, 0)
                ).label('practice_cnt'),
                func.sum(
                    func.if_(LearningRecord.record_type == 'correction', 1, 0)
                ).label('correction_cnt'),
                func.sum(
                    func.if_(
                        LearningRecord.record_type == 'practice',
                        LearningRecord.question_count,
                        0,
                    )
                ).label('question_cnt'),
                func.sum(
                    func.if_(
                        LearningRecord.record_type == 'practice',
                        LearningRecord.correct_count,
                        0,
                    )
                ).label('correct_cnt'),
                func.sum(LearningRecord.mastery_change).label('total_mastery_change'),
            ).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.record_type.in_(['practice', 'correction']),
                    LearningRecord.occurred_at >= f"{date_from} 00:00:00",
                    LearningRecord.occurred_at <= f"{date_to} 23:59:59",
                    LearningRecord.subject == subject if subject else True,
                )
            )
            row = (await session.execute(q)).fetchone()

            numeric = (int, float, Decimal)
            question_count = int(row.question_cnt or 0)
            correct_value = getattr(row, "correct_cnt", None)
            correct_count = int(correct_value or 0) if isinstance(correct_value, numeric) else 0
            legacy_accuracy = getattr(row, "avg_acc", None)
            accuracy = (
                round(correct_count * 100 / question_count, 2)
                if question_count and isinstance(correct_value, numeric)
                else round(float(legacy_accuracy), 2)
                if isinstance(legacy_accuracy, numeric)
                else 0.0
            )
            practice_value = getattr(row, "practice_cnt", 0)
            correction_value = getattr(row, "correction_cnt", 0)
            return {
                "practice_count": int(practice_value or 0)
                if isinstance(practice_value, numeric) else 0,
                "correction_count": int(correction_value or 0)
                if isinstance(correction_value, numeric) else 0,
                "question_count": question_count,
                "correct_count": correct_count,
                "accuracy": accuracy,
                "mastery_change": int(row.total_mastery_change or 0),
            }

    async def _add_detailed_analysis(
        self, data: Dict, user_id: int, date_from: str, date_to: str
    ) -> None:
        """详情增强失败时仍返回已持久化的基础报告，避免历史报告不可打开。"""
        try:
            data.update(await self._build_detailed_analysis(user_id, date_from, date_to))
            data.update(await self._build_subject_reports(user_id, date_from, date_to))
        except Exception as exc:
            logger.warning("Detailed report analysis failed for user=%s: %s", user_id, exc)

    async def _build_detailed_analysis(
        self,
        user_id: int,
        date_from: str,
        date_to: str,
        subject: Optional[str] = None,
    ) -> Dict:
        """构建可解释的报告详情；历史报告也按其原始日期区间实时补全。"""
        current = await self._gather_stats(user_id, date_from, date_to, subject)
        started = date.fromisoformat(date_from)
        ended = date.fromisoformat(date_to)
        period_days = (ended - started).days + 1
        previous_to = started - timedelta(days=1)
        previous_from = previous_to - timedelta(days=period_days - 1)
        previous = await self._gather_stats(
            user_id, previous_from.isoformat(), previous_to.isoformat(), subject
        )
        query_params = {
            "uid": user_id,
            "subject": subject,
            "started_at": f"{date_from} 00:00:00",
            "ended_at": f"{date_to} 23:59:59",
        }

        async with AsyncSessionLocal() as session:
            knowledge_rows = (
                await session.execute(
                    text(
                        """
                        SELECT knowledge_point_name,
                               SUM(question_count) AS question_count,
                               SUM(correct_count) AS correct_count,
                               COUNT(*) AS session_count
                        FROM learning_record
                        WHERE user_id = :uid
                          AND record_type = 'practice'
                          AND (:subject IS NULL OR subject = :subject)
                          AND knowledge_point_name IS NOT NULL
                          AND knowledge_point_name NOT IN ('综合知识点', '其他', '未知知识点')
                          AND occurred_at BETWEEN :started_at AND :ended_at
                        GROUP BY knowledge_point_name
                        ORDER BY
                          SUM(correct_count) / NULLIF(SUM(question_count), 0) ASC,
                          SUM(question_count) DESC
                        """
                    ),
                    query_params,
                )
            ).mappings().all()

            mastery_rows = (
                await session.execute(
                    text(
                        """
                        SELECT knowledge_point_name, mastery_score, learning_status
                        FROM knowledge_mastery
                        WHERE user_id = :uid
                          AND knowledge_point_name NOT IN ('综合知识点', '其他', '未知知识点')
                        """
                    ),
                    {"uid": user_id},
                )
            ).mappings().all()
            mastery_map = {row["knowledge_point_name"]: row for row in mastery_rows}

            daily_rows = (
                await session.execute(
                    text(
                        """
                        SELECT DATE(occurred_at) AS study_date,
                               SUM(question_count) AS question_count,
                               SUM(correct_count) AS correct_count,
                               COUNT(*) AS session_count
                        FROM learning_record
                        WHERE user_id = :uid
                          AND record_type = 'practice'
                          AND (:subject IS NULL OR subject = :subject)
                          AND occurred_at BETWEEN :started_at AND :ended_at
                        GROUP BY DATE(occurred_at)
                        ORDER BY study_date
                        """
                    ),
                    query_params,
                )
            ).mappings().all()

            error_rows = (
                await session.execute(
                    text(
                        """
                        SELECT error_type, COUNT(*) AS error_count
                        FROM mistake
                        WHERE user_id = :uid
                          AND error_type IS NOT NULL
                          AND (:subject IS NULL OR subject = :subject)
                          AND created_at BETWEEN :started_at AND :ended_at
                        GROUP BY error_type
                        ORDER BY error_count DESC
                        """
                    ),
                    query_params,
                )
            ).mappings().all()

            review_row = (
                await session.execute(
                    select(
                        func.count(KnowledgeReviewRecord.id).label("review_count"),
                        func.sum(KnowledgeReviewRecord.quiz_score).label("quiz_score"),
                        func.sum(KnowledgeReviewRecord.quiz_total).label("quiz_total"),
                    ).where(
                        KnowledgeReviewRecord.user_id == user_id,
                        KnowledgeReviewRecord.completed_at >= f"{date_from} 00:00:00",
                        KnowledgeReviewRecord.completed_at <= f"{date_to} 23:59:59",
                        KnowledgeReviewRecord.subject == subject if subject else True,
                    )
                )
            ).one()

        knowledge_breakdown = []
        for row in knowledge_rows:
            questions = int(row["question_count"] or 0)
            correct = int(row["correct_count"] or 0)
            accuracy = round(correct * 100 / questions, 1) if questions else 0.0
            mastery = mastery_map.get(row["knowledge_point_name"])
            knowledge_breakdown.append({
                "name": row["knowledge_point_name"],
                "question_count": questions,
                "correct_count": correct,
                "accuracy": accuracy,
                "session_count": int(row["session_count"] or 0),
                "mastery_score": int(mastery["mastery_score"]) if mastery else None,
                "learning_status": mastery["learning_status"] if mastery else None,
            })

        daily_trend = []
        for row in daily_rows:
            questions = int(row["question_count"] or 0)
            correct = int(row["correct_count"] or 0)
            daily_trend.append({
                "date": row["study_date"].isoformat(),
                "question_count": questions,
                "correct_count": correct,
                "accuracy": round(correct * 100 / questions, 1) if questions else 0.0,
                "session_count": int(row["session_count"] or 0),
            })

        error_total = sum(int(row["error_count"]) for row in error_rows)
        error_distribution = [{
            "type": row["error_type"],
            "count": int(row["error_count"]),
            "percentage": round(int(row["error_count"]) * 100 / error_total, 1)
            if error_total else 0.0,
        } for row in error_rows]

        strengths = [item for item in knowledge_breakdown if item["accuracy"] >= 80]
        weak_details = [item for item in knowledge_breakdown if item["accuracy"] < 70]
        action_plan = self._generate_action_plan(weak_details, error_distribution, current)
        has_previous_data = previous["question_count"] > 0
        accuracy_delta = (
            round(current["accuracy"] - previous["accuracy"], 1)
            if has_previous_data else None
        )

        return {
            "overview": {
                **current,
                "study_days": len(daily_trend),
                "period_days": period_days,
                "wrong_count": max(current["question_count"] - current["correct_count"], 0),
                "knowledge_review_count": int(review_row.review_count or 0),
                "concept_quiz_accuracy": round(
                    int(review_row.quiz_score or 0) * 100 / int(review_row.quiz_total or 0), 1
                ) if review_row.quiz_total else None,
            },
            "comparison": {
                "previous_date_from": previous_from.isoformat(),
                "previous_date_to": previous_to.isoformat(),
                "has_previous_data": has_previous_data,
                "accuracy_delta": accuracy_delta,
                "question_delta": current["question_count"] - previous["question_count"],
                "practice_delta": current["practice_count"] - previous["practice_count"],
                "previous_accuracy": previous["accuracy"],
            },
            "daily_trend": daily_trend,
            "knowledge_breakdown": knowledge_breakdown,
            "strengths": strengths[:3],
            "weak_details": weak_details[:3],
            "error_distribution": error_distribution,
            "action_plan": action_plan,
            "summary": self._generate_summary(
                current, accuracy_delta, weak_details, has_previous_data
            ),
        }

    async def _build_subject_reports(
        self, user_id: int, date_from: str, date_to: str
    ) -> Dict:
        """按中小学学科或大学课程生成子报告；无数据项由前端展示空状态。"""
        async with AsyncSessionLocal() as session:
            profile = (
                await session.execute(
                    select(UserProfile).where(UserProfile.user_id == user_id)
                )
            ).scalar_one_or_none()
            rows = (
                await session.execute(
                    select(LearningRecord.subject)
                    .where(
                        LearningRecord.user_id == user_id,
                        LearningRecord.record_type == "practice",
                        LearningRecord.subject.is_not(None),
                        LearningRecord.subject != "",
                        LearningRecord.occurred_at >= f"{date_from} 00:00:00",
                        LearningRecord.occurred_at <= f"{date_to} 23:59:59",
                    )
                    .distinct()
                    .order_by(LearningRecord.subject)
                )
            ).scalars().all()

        active_subjects = list(rows)
        subject_reports = {}
        for item in active_subjects:
            report = await self._build_detailed_analysis(
                user_id, date_from, date_to, subject=item
            )
            report["subject"] = item
            report["has_data"] = report["overview"]["question_count"] > 0
            report["sample_sufficient"] = report["overview"]["question_count"] >= 5
            subject_reports[item] = report

        stage = profile.stage if profile else ""
        return {
            "report_scope": {
                "stage": stage,
                "mode": "course" if stage == "university" else "subject",
                "available_subjects": active_subjects,
            },
            "subject_reports": subject_reports,
        }

    def _generate_action_plan(
        self, weak_details: List[Dict], errors: List[Dict], stats: Dict
    ) -> List[Dict]:
        plans = []
        for index, item in enumerate(weak_details[:2], start=1):
            plans.append({
                "priority": index,
                "title": f"专项巩固「{item['name']}」",
                "reason": (
                    f"本阶段完成 {item['question_count']} 题，正确率仅 "
                    f"{item['accuracy']:.0f}%"
                ),
                "target": "先复习概念与例题，再完成 2 组由易到难的专项练习，目标正确率达到 80%",
            })
        if errors:
            error_map = {
                "knowledge": ("修补概念漏洞", "每次错题写出所用概念或公式，并完成一道同类变式题"),
                "calculation": ("降低计算失误", "保留分步过程并在提交前反向验算，连续完成 5 题零计算错误"),
                "reading": ("强化审题提取", "圈出条件、问题和限制词，再用自己的话复述题意后作答"),
                "method": ("建立解题方法库", "对同类题总结固定步骤，并比较至少两种解法的适用条件"),
            }
            title, target = error_map.get(
                errors[0]["type"], ("针对高频错因复盘", "订正本阶段错题并完成同类变式练习")
            )
            plans.append({
                "priority": len(plans) + 1,
                "title": title,
                "reason": f"该错因占本阶段错题的 {errors[0]['percentage']:.0f}%",
                "target": target,
            })
        if not plans:
            plans.append({
                "priority": 1,
                "title": "保持并适度进阶",
                "reason": f"本阶段整体正确率 {stats['accuracy']:.0f}%，暂无明显低分知识点",
                "target": "保持当前频率，下一阶段加入中等难度综合应用题",
            })
        return plans[:3]

    @staticmethod
    def _generate_summary(
        stats: Dict,
        accuracy_delta: Optional[float],
        weak_details: List[Dict],
        has_previous_data: bool,
    ) -> str:
        if not has_previous_data:
            trend = "上一阶段暂无可比数据，本报告将作为后续对比基线"
        else:
            trend = "较上一阶段提升" if accuracy_delta > 0 else (
                "较上一阶段回落" if accuracy_delta < 0 else "与上一阶段持平"
            )
            trend += f" {abs(accuracy_delta):.1f} 个百分点"
        weak_text = (
            f"当前首要薄弱点是「{weak_details[0]['name']}」"
            if weak_details else "当前没有明显低于 70% 的知识点"
        )
        return (
            f"本阶段完成 {stats['question_count']} 题，整体正确率 "
            f"{stats['accuracy']:.0f}%，{trend}；"
            f"{weak_text}。"
        )

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
