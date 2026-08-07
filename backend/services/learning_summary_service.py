"""成员二 用户端 Service：个人学情摘要聚合。

职责（对齐《五人任务分工》第 4.2 / 4.4 节 + 契约第 3 节 `/mastery/*`）：
- 首页学习概览 / 学情摘要：总体掌握度、知识点掌握度分布、薄弱知识点；
- 待订正错题数、今日到期复习数，引导用户下一步学习动作。

只读、只聚合“当前登录用户自己”的数据（user_id 一律来自 JWT）。
掌握度分桶（weak/consolidating/mastered）与统计时区（东八区）与运营看板保持一致，
保证“用户看到的自己”与“管理员看到的聚合”口径统一。
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func, case

from backend.model import AsyncSessionLocal
from backend.model.mastery import KnowledgeMastery, Mistake, ReviewPlan

# 东八区：与运营看板 (admin_dashboard_service) 保持同一业务时区
_TZ = timezone(timedelta(hours=8))

# 与运营看板一致的状态中文标签
_STATUS_LABEL = {
    "weak": "薄弱",
    "consolidating": "巩固中",
    "mastered": "已掌握",
}


def _today() -> date:
    return datetime.now(_TZ).date()


class LearningSummaryService:
    """当前用户的学情摘要：只读聚合。"""

    async def get_summary(self, user_id: int, weak_limit: int = 5) -> dict:
        """返回单个用户的学情摘要。

        口径说明（与运营看板 mastery_distribution 对齐）：
        - total_knowledge_points：该用户已建立掌握度记录的知识点数；
        - studied_count：其中已有答题证据（answer_count > 0）的知识点数；
        - overall_score：仅对“有答题证据”的知识点取 mastery_score 平均，
          避免尚未作答的中性初值（50）稀释总体掌握度；无证据时为 0；
        - distribution：knowledge_mastery 按 learning_status 分桶计数；
        - weakest：薄弱知识点 Top N（按掌握度升序），用于引导针对性练习；
        - pending_corrections：待订正错题数（correction_status='pending'）；
        - due_reviews：今日及以前到期且未完成的复习计划数。
        """
        today = _today()
        async with AsyncSessionLocal() as db:
            # 知识点总数与已作答数
            count_row = (
                await db.execute(
                    select(
                        func.count(KnowledgeMastery.id).label("total"),
                        func.sum(
                            case((KnowledgeMastery.answer_count > 0, 1), else_=0)
                        ).label("studied"),
                    ).where(KnowledgeMastery.user_id == user_id)
                )
            ).one()
            total_kp = int(count_row.total or 0)
            studied_count = int(count_row.studied or 0)

            # 总体掌握度：仅统计有答题证据的知识点
            overall_score = (
                await db.execute(
                    select(func.avg(KnowledgeMastery.mastery_score)).where(
                        KnowledgeMastery.user_id == user_id,
                        KnowledgeMastery.answer_count > 0,
                    )
                )
            ).scalar()
            overall_score = round(float(overall_score)) if overall_score is not None else 0

            # 掌握度分布
            dist_rows = (
                await db.execute(
                    select(
                        KnowledgeMastery.learning_status,
                        func.count(KnowledgeMastery.id),
                    )
                    .where(KnowledgeMastery.user_id == user_id)
                    .group_by(KnowledgeMastery.learning_status)
                )
            ).all()
            dist_map = {status: cnt for status, cnt in dist_rows}
            distribution = [
                {
                    "status": s,
                    "label": _STATUS_LABEL[s],
                    "count": int(dist_map.get(s, 0)),
                }
                for s in ("weak", "consolidating", "mastered")
            ]

            # 薄弱知识点 Top N（有答题证据、掌握度最低者优先）
            weak_rows = (
                await db.execute(
                    select(
                        KnowledgeMastery.knowledge_point_name,
                        KnowledgeMastery.mastery_score,
                        KnowledgeMastery.learning_status,
                    )
                    .where(
                        KnowledgeMastery.user_id == user_id,
                        KnowledgeMastery.answer_count > 0,
                    )
                    .order_by(KnowledgeMastery.mastery_score.asc())
                    .limit(weak_limit)
                )
            ).all()
            weakest = [
                {
                    "knowledge_point_name": r.knowledge_point_name,
                    "mastery_score": int(r.mastery_score),
                    "learning_status": r.learning_status,
                }
                for r in weak_rows
                if r.learning_status != "mastered"
            ]

            # 待订正错题数
            pending_corrections = (
                await db.execute(
                    select(func.count(Mistake.id)).where(
                        Mistake.user_id == user_id,
                        Mistake.correction_status == "pending",
                    )
                )
            ).scalar() or 0

            # 今日及以前到期、未完成的复习数
            due_reviews = (
                await db.execute(
                    select(func.count(ReviewPlan.id)).where(
                        ReviewPlan.user_id == user_id,
                        ReviewPlan.status == "pending",
                        ReviewPlan.review_date <= today,
                    )
                )
            ).scalar() or 0

            return {
                "overall_score": overall_score,
                "total_knowledge_points": total_kp,
                "studied_count": studied_count,
                "distribution": distribution,
                "weakest": weakest,
                "pending_corrections": int(pending_corrections),
                "due_reviews": int(due_reviews),
            }


learning_summary_service = LearningSummaryService()
