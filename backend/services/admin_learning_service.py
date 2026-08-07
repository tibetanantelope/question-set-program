"""成员四 管理员端 Service：错题统计、复习情况、薄弱知识点、学习轨迹摘要。"""

import math
from datetime import date, datetime
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.model import AsyncSessionLocal
from backend.model.mastery import Mistake, ReviewPlan, KnowledgeMastery
from backend.model.learning_models import LearningRecord, LearningReport
from backend.model.user import User
from backend.core.exceptions import BusinessError

_ERROR_MAP = {
    "knowledge": "概念不清",
    "calculation": "计算错误",
    "reading": "审题错误",
    "method": "方法不对",
}


class AdminLearningService:
    """管理员端学习管理 Service：只读，不修改用户数据。"""

    # ─── 错题统计 ─────────────────────────────

    async def get_mistake_stats(
        self,
        user_id: int | None = None,
        subject: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """按用户维度聚合错题统计（数量、主要错因、订正率）。"""
        async with AsyncSessionLocal() as db:
            # 基础条件
            conditions = []
            if user_id:
                conditions.append(Mistake.user_id == user_id)
            if subject:
                conditions.append(Mistake.subject == subject)

            base = select(Mistake).where(*conditions) if conditions else select(Mistake)

            # 按用户聚合
            agg_stmt = (
                select(
                    Mistake.user_id,
                    func.count(Mistake.id).label("total_mistakes"),
                    func.sum(
                        case((Mistake.correction_status == "corrected", 1), else_=0)
                    ).label("corrected_count"),
                    func.sum(
                        case((Mistake.correction_status == "pending", 1), else_=0)
                    ).label("pending_count"),
                    func.sum(
                        case((Mistake.correction_status == "review_due", 1), else_=0)
                    ).label("review_due_count"),
                )
                .where(*conditions) if conditions else select(
                    Mistake.user_id,
                    func.count(Mistake.id).label("total_mistakes"),
                    func.sum(
                        case((Mistake.correction_status == "corrected", 1), else_=0)
                    ).label("corrected_count"),
                    func.sum(
                        case((Mistake.correction_status == "pending", 1), else_=0)
                    ).label("pending_count"),
                    func.sum(
                        case((Mistake.correction_status == "review_due", 1), else_=0)
                    ).label("review_due_count"),
                )
                .group_by(Mistake.user_id)
                .order_by(func.count(Mistake.id).desc())
            )

            # 总数
            count_subq = (
                select(func.count(func.distinct(Mistake.user_id)))
            )
            if conditions:
                count_subq = count_subq.where(*conditions)
            total_res = await db.execute(count_subq)
            total = total_res.scalar() or 0

            # 分页
            offset = (page - 1) * page_size
            agg_stmt = agg_stmt.offset(offset).limit(page_size)
            agg_res = await db.execute(agg_stmt)
            rows = agg_res.all()

            # 按用户ID批量取错因
            user_ids = [r.user_id for r in rows if r.user_id]
            error_map = {}
            if user_ids:
                for uid in user_ids:
                    err_stmt = (
                        select(
                            Mistake.error_type,
                            func.count(Mistake.id).label("cnt"),
                        )
                        .where(Mistake.user_id == uid)
                        .group_by(Mistake.error_type)
                        .order_by(func.count(Mistake.id).desc())
                    )
                    err_res = await db.execute(err_stmt)
                    errs = err_res.all()
                    if errs:
                        top = errs[0]
                        error_map[uid] = {
                            "top_error_type": top.error_type,
                            "top_error_label": _ERROR_MAP.get(top.error_type, top.error_type or "未知"),
                            "error_breakdown": [
                                {"type": e.error_type, "label": _ERROR_MAP.get(e.error_type, e.error_type or "未知"), "count": e.cnt}
                                for e in errs[:5]
                            ],
                        }

            # 取用户名
            username_map = {}
            if user_ids:
                user_res = await db.execute(
                    select(User.id, User.username).where(User.id.in_(user_ids))
                )
                username_map = {u.id: u.username for u in user_res.all()}

            items = []
            for r in rows:
                correction_rate = round(r.corrected_count / r.total_mistakes * 100, 1) if r.total_mistakes > 0 else 0.0
                items.append({
                    "user_id": r.user_id,
                    "username": username_map.get(r.user_id, "未知用户"),
                    "total_mistakes": r.total_mistakes,
                    "corrected_count": r.corrected_count or 0,
                    "pending_count": r.pending_count or 0,
                    "review_due_count": r.review_due_count or 0,
                    "correction_rate": correction_rate,
                    **error_map.get(r.user_id, {"top_error_type": None, "top_error_label": None, "error_breakdown": []}),
                })

            pages = math.ceil(total / page_size) if total > 0 else 0
            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": pages,
            }

    # ─── 复习情况 ─────────────────────────────

    async def get_review_stats(
        self,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """查看复习完成率和到期复习情况。"""
        async with AsyncSessionLocal() as db:
            conditions = []
            if user_id:
                conditions.append(ReviewPlan.user_id == user_id)

            base = (
                select(ReviewPlan).where(*conditions)
                if conditions
                else select(ReviewPlan)
            )

            # 按用户聚合
            agg_stmt = (
                select(
                    ReviewPlan.user_id,
                    func.count(ReviewPlan.id).label("total_reviews"),
                    func.sum(
                        case((ReviewPlan.status == "completed", 1), else_=0)
                    ).label("completed_count"),
                    func.sum(
                        case((ReviewPlan.status == "pending", 1), else_=0)
                    ).label("pending_count"),
                    func.sum(
                        case(
                            (
                                and_(
                                    ReviewPlan.status == "pending",
                                    ReviewPlan.review_date <= date.today(),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("overdue_count"),
                )
                .group_by(ReviewPlan.user_id)
                .order_by(func.count(ReviewPlan.id).desc())
            )
            if conditions:
                agg_stmt = agg_stmt.where(*conditions)

            # 总数
            count_stmt = select(func.count(func.distinct(ReviewPlan.user_id)))
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = (await db.execute(count_stmt)).scalar() or 0

            offset = (page - 1) * page_size
            agg_stmt = agg_stmt.offset(offset).limit(page_size)
            res = await db.execute(agg_stmt)
            rows = res.all()

            user_ids = [r.user_id for r in rows]
            username_map = {}
            if user_ids:
                user_res = await db.execute(
                    select(User.id, User.username).where(User.id.in_(user_ids))
                )
                username_map = {u.id: u.username for u in user_res.all()}

            items = []
            for r in rows:
                completion_rate = round(r.completed_count / r.total_reviews * 100, 1) if r.total_reviews > 0 else 0.0
                items.append({
                    "user_id": r.user_id,
                    "username": username_map.get(r.user_id, "未知用户"),
                    "total_reviews": r.total_reviews,
                    "completed_count": r.completed_count or 0,
                    "pending_count": r.pending_count or 0,
                    "overdue_count": r.overdue_count or 0,
                    "completion_rate": completion_rate,
                })

            pages = math.ceil(total / page_size) if total > 0 else 0
            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": pages,
            }

    # ─── 薄弱知识点 ───────────────────────────

    async def get_weak_points(
        self,
        user_id: int | None = None,
        subject: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """查看用户薄弱知识点（掌握度 < 60 的条目）。"""
        async with AsyncSessionLocal() as db:
            conditions = [KnowledgeMastery.mastery_score < 60]
            if user_id:
                conditions.append(KnowledgeMastery.user_id == user_id)
            # KnowledgeMastery has no subject column, skip subject filter for weak points

            count_stmt = (
                select(func.count(KnowledgeMastery.id)).where(*conditions)
            )
            total = (await db.execute(count_stmt)).scalar() or 0

            offset = (page - 1) * page_size
            stmt = (
                select(KnowledgeMastery)
                .where(*conditions)
                .order_by(KnowledgeMastery.mastery_score.asc())
                .offset(offset)
                .limit(page_size)
            )
            res = await db.execute(stmt)
            rows = res.scalars().all()

            user_ids = list(set(r.user_id for r in rows if r.user_id))
            username_map = {}
            if user_ids:
                user_res = await db.execute(
                    select(User.id, User.username).where(User.id.in_(user_ids))
                )
                username_map = {u.id: u.username for u in user_res.all()}

            items = [
                {
                    "user_id": r.user_id,
                    "username": username_map.get(r.user_id, "未知用户"),
                    "knowledge_point_id": r.knowledge_point_id,
                    "knowledge_point_name": r.knowledge_point_name,
                    "mastery_score": r.mastery_score,
                    "learning_status": r.learning_status,
                    "answer_count": r.answer_count or 0,
                    "correct_count": r.correct_count or 0,
                    "subject": getattr(r, "subject", None),
                    "last_studied_at": (
                        r.last_studied_at.isoformat() if r.last_studied_at else None
                    ),
                }
                for r in rows
            ]

            pages = math.ceil(total / page_size) if total > 0 else 0
            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": pages,
            }

    # ─── 用户学习轨迹摘要 ──────────────────────

    async def get_user_learning_summary(self, user_id: int) -> dict:
        """查看单个用户的学习轨迹摘要。"""
        async with AsyncSessionLocal() as db:
            # 用户基础信息
            user_res = await db.execute(
                select(User).where(User.id == user_id)
            )
            user_row = user_res.scalar_one_or_none()
            if not user_row:
                raise BusinessError("USER_NOT_FOUND", "用户不存在", 404)

            # 错题统计
            mistake_stmt = (
                select(
                    func.count(Mistake.id).label("total"),
                    func.sum(
                        case((Mistake.correction_status == "corrected", 1), else_=0)
                    ).label("corrected"),
                    func.sum(
                        case((Mistake.correction_status == "pending", 1), else_=0)
                    ).label("pending"),
                ).where(Mistake.user_id == user_id)
            )
            mistake_res = await db.execute(mistake_stmt)
            mistake_row = mistake_res.one()

            # 复习统计
            review_stmt = (
                select(
                    func.count(ReviewPlan.id).label("total"),
                    func.sum(
                        case((ReviewPlan.status == "completed", 1), else_=0)
                    ).label("completed"),
                    func.sum(
                        case(
                            (
                                and_(
                                    ReviewPlan.status == "pending",
                                    ReviewPlan.review_date <= date.today(),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("overdue"),
                ).where(ReviewPlan.user_id == user_id)
            )
            review_res = await db.execute(review_stmt)
            review_row = review_res.one()

            # 学习记录统计
            record_stmt = (
                select(
                    func.count(LearningRecord.id).label("total"),
                    func.max(LearningRecord.occurred_at).label("last_active"),
                ).where(LearningRecord.user_id == user_id)
            )
            record_res = await db.execute(record_stmt)
            record_row = record_res.one()

            # 报告统计
            report_stmt = (
                select(
                    func.count(LearningReport.id).label("total"),
                    func.max(LearningReport.created_at).label("last_report"),
                ).where(LearningReport.user_id == user_id)
            )
            report_res = await db.execute(report_stmt)
            report_row = report_res.one()

            # 薄弱知识点 TOP5
            kp_stmt = (
                select(KnowledgeMastery)
                .where(
                    KnowledgeMastery.user_id == user_id,
                    KnowledgeMastery.mastery_score < 80,
                )
                .order_by(KnowledgeMastery.mastery_score.asc())
                .limit(5)
            )
            kp_res = await db.execute(kp_stmt)
            weak_kps = kp_res.scalars().all()

            # 最近学习记录
            recent_stmt = (
                select(LearningRecord)
                .where(LearningRecord.user_id == user_id)
                .order_by(LearningRecord.occurred_at.desc())
                .limit(10)
            )
            recent_res = await db.execute(recent_stmt)
            recent_records = recent_res.scalars().all()

            correction_rate = (
                round(
                    (mistake_row.corrected or 0) / mistake_row.total * 100, 1
                )
                if mistake_row.total > 0
                else 0.0
            )
            review_completion_rate = (
                round(
                    (review_row.completed or 0) / review_row.total * 100, 1
                )
                if review_row.total > 0
                else 0.0
            )

            return {
                "user": {
                    "user_id": user_row.id,
                    "username": user_row.username,
                    "status": user_row.status,
                },
                "mistake_summary": {
                    "total": mistake_row.total or 0,
                    "corrected": mistake_row.corrected or 0,
                    "pending": mistake_row.pending or 0,
                    "correction_rate": correction_rate,
                },
                "review_summary": {
                    "total": review_row.total or 0,
                    "completed": review_row.completed or 0,
                    "overdue": review_row.overdue or 0,
                    "completion_rate": review_completion_rate,
                },
                "learning_summary": {
                    "total_records": record_row.total or 0,
                    "last_active": record_row.last_active.isoformat() if record_row.last_active else None,
                },
                "report_summary": {
                    "total_reports": report_row.total or 0,
                    "last_report": report_row.last_report.isoformat() if report_row.last_report else None,
                },
                "weak_knowledge_points": [
                    {
                        "knowledge_point_id": kp.knowledge_point_id,
                        "knowledge_point_name": kp.knowledge_point_name,
                        "mastery_score": kp.mastery_score,
                        "learning_status": kp.learning_status,
                        "subject": getattr(kp, "subject", None),
                    }
                    for kp in weak_kps
                ],
                "recent_records": [
                    {
                        "record_id": rec.id,
                        "record_type": rec.record_type,
                        "title": rec.title,
                        "subject": rec.subject,
                        "knowledge_point_name": rec.knowledge_point_name,
                        "accuracy": float(rec.accuracy) if rec.accuracy is not None else None,
                        "occurred_at": rec.occurred_at.isoformat() if rec.occurred_at else None,
                    }
                    for rec in recent_records
                ],
            }


admin_learning_service = AdminLearningService()
