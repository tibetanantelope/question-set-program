"""成员二 管理员端 Service：运营看板聚合统计。

职责（对齐《五人任务分工》第 4 节 + 契约第 3 节 `/admin/dashboard/*`）：
- 运营首页统计卡片：总用户数、活跃用户数、新增用户数；
- 练习次数、完成率、平均正确率；
- 错题数量、复习完成率、掌握度分布；
- 学科分布与近 7/30 天趋势。

只读、只返回聚合数据，不泄露单个用户隐私明细，也不修改任何用户数据。
统计口径统一按 Asia/Shanghai（东八区）计算业务日。
"""

import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func, case, and_

from backend.model import AsyncSessionLocal
from backend.model.user import User
from backend.model.learning import Practice
from backend.model.mastery import Mistake, ReviewPlan, KnowledgeMastery
from backend.model.learning_models import LearningRecord

# 东八区：业务日、活跃、新增等指标统一按此时区归日
_TZ = timezone(timedelta(hours=8))

_STATUS_LABEL = {
    "weak": "薄弱",
    "consolidating": "巩固中",
    "mastered": "已掌握",
}


def _now() -> datetime:
    return datetime.now(_TZ)


def _range_start(days: int) -> datetime:
    """返回统计窗口起点（含当天，共 days 天）的东八区零点。"""
    today = _now().date()
    start_day = today - timedelta(days=days - 1)
    return datetime.combine(start_day, datetime.min.time(), tzinfo=_TZ)


class AdminDashboardService:
    """管理员运营看板：聚合只读统计。"""

    # ─── 运营总览卡片 ─────────────────────────────

    async def get_overview(self, days: int = 7) -> dict:
        """运营首页统计卡片。

        days：活跃用户和新增用户的统计窗口（默认近 7 天）。

        口径说明：
        - total_users：角色为普通用户（role='user'）的账号总数；
        - active_users：统计窗口内产生过学习记录的去重用户数；
        - new_users：首次学习记录落在统计窗口内的用户数（User 表无注册时间，
          以“首次学习行为”作为新增代理口径，并在契约中标注）；
        - practice_* / accuracy：基于 practice 表；完成率 = 已完成 / 总数；
          平均正确率仅统计已完成练习，避免进行中练习拉低口径；
        - mistake_total / review_completion_rate：错题与复习计划聚合；
        - mastery_distribution：knowledge_mastery 按 learning_status 分布。
        """
        window_start = _range_start(days)
        async with AsyncSessionLocal() as db:
            # 总用户数（仅普通用户）
            total_users = (
                await db.execute(
                    select(func.count(User.id)).where(User.role == "user")
                )
            ).scalar() or 0

            # 活跃用户数：窗口内有学习记录的去重用户
            active_users = (
                await db.execute(
                    select(func.count(func.distinct(LearningRecord.user_id))).where(
                        LearningRecord.occurred_at >= window_start
                    )
                )
            ).scalar() or 0

            # 新增用户数：首次学习记录落在窗口内的用户
            first_seen_subq = (
                select(
                    LearningRecord.user_id.label("uid"),
                    func.min(LearningRecord.occurred_at).label("first_at"),
                )
                .group_by(LearningRecord.user_id)
                .subquery()
            )
            new_users = (
                await db.execute(
                    select(func.count()).select_from(first_seen_subq).where(
                        first_seen_subq.c.first_at >= window_start
                    )
                )
            ).scalar() or 0

            # 练习统计
            practice_row = (
                await db.execute(
                    select(
                        func.count(Practice.id).label("total"),
                        func.sum(
                            case((Practice.status == "completed", 1), else_=0)
                        ).label("completed"),
                    )
                )
            ).one()
            practice_total = practice_row.total or 0
            practice_completed = practice_row.completed or 0
            completion_rate = (
                round(practice_completed / practice_total * 100, 1)
                if practice_total > 0
                else 0.0
            )

            # 平均正确率：仅统计已完成练习
            avg_accuracy = (
                await db.execute(
                    select(func.avg(Practice.accuracy)).where(
                        Practice.status == "completed"
                    )
                )
            ).scalar()
            # accuracy 入库时已是百分数（0–100），此处不再二次乘 100
            avg_accuracy = round(float(avg_accuracy), 1) if avg_accuracy else 0.0

            # 错题总数
            mistake_total = (
                await db.execute(select(func.count(Mistake.id)))
            ).scalar() or 0

            # 复习完成率
            review_row = (
                await db.execute(
                    select(
                        func.count(ReviewPlan.id).label("total"),
                        func.sum(
                            case((ReviewPlan.status == "completed", 1), else_=0)
                        ).label("completed"),
                    )
                )
            ).one()
            review_total = review_row.total or 0
            review_completed = review_row.completed or 0
            review_completion_rate = (
                round(review_completed / review_total * 100, 1)
                if review_total > 0
                else 0.0
            )

            # 掌握度分布
            dist_rows = (
                await db.execute(
                    select(
                        KnowledgeMastery.learning_status,
                        func.count(KnowledgeMastery.id),
                    ).group_by(KnowledgeMastery.learning_status)
                )
            ).all()
            dist_map = {status: cnt for status, cnt in dist_rows}
            mastery_distribution = [
                {
                    "status": s,
                    "label": _STATUS_LABEL[s],
                    "count": int(dist_map.get(s, 0)),
                }
                for s in ("weak", "consolidating", "mastered")
            ]

            return {
                "days": days,
                "user_stats": {
                    "total_users": int(total_users),
                    "active_users": int(active_users),
                    "new_users": int(new_users),
                },
                "practice_stats": {
                    "practice_total": int(practice_total),
                    "practice_completed": int(practice_completed),
                    "completion_rate": completion_rate,
                    "avg_accuracy": avg_accuracy,
                },
                "mistake_stats": {
                    "mistake_total": int(mistake_total),
                    "review_total": int(review_total),
                    "review_completed": int(review_completed),
                    "review_completion_rate": review_completion_rate,
                },
                "mastery_distribution": mastery_distribution,
            }

    # ─── 学科分布 ─────────────────────────────────

    async def get_subject_distribution(self) -> dict:
        """按学科聚合练习次数与平均正确率（学科趋势的横截面）。"""
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(
                        Practice.subject,
                        func.count(Practice.id).label("practice_count"),
                        func.avg(
                            case(
                                (Practice.status == "completed", Practice.accuracy),
                                else_=None,
                            )
                        ).label("avg_accuracy"),
                    )
                    .group_by(Practice.subject)
                    .order_by(func.count(Practice.id).desc())
                )
            ).all()

            items = [
                {
                    "subject": r.subject or "未分类",
                    "practice_count": int(r.practice_count or 0),
                    # accuracy 入库时已是百分数（0–100），此处不再二次乘 100
                    "avg_accuracy": (
                        round(float(r.avg_accuracy), 1) if r.avg_accuracy else 0.0
                    ),
                }
                for r in rows
            ]
            return {"items": items}

    # ─── 近 N 天趋势 ──────────────────────────────

    async def get_trend(self, days: int = 7) -> dict:
        """近 N 天学习活跃趋势：每天的练习次数与活跃用户数。

        对没有数据的日期补零，保证前端折线连续、便于展示空数据状态。
        """
        if days < 1:
            days = 1
        window_start = _range_start(days)
        today = _now().date()

        async with AsyncSessionLocal() as db:
            # func.date() 在 sqlite / mysql 下都会把 datetime 归到日粒度
            day_col = func.date(LearningRecord.occurred_at)
            rows = (
                await db.execute(
                    select(
                        day_col.label("day"),
                        func.count(LearningRecord.id).label("record_count"),
                        func.count(func.distinct(LearningRecord.user_id)).label(
                            "active_users"
                        ),
                    )
                    .where(LearningRecord.occurred_at >= window_start)
                    .group_by(day_col)
                    .order_by(day_col.asc())
                )
            ).all()

            # 归一化 key 为 ISO 日期字符串
            by_day = {}
            for r in rows:
                d = r.day
                key = d.isoformat() if isinstance(d, (date, datetime)) else str(d)
                by_day[key] = {
                    "record_count": int(r.record_count or 0),
                    "active_users": int(r.active_users or 0),
                }

            points = []
            for i in range(days):
                d = today - timedelta(days=days - 1 - i)
                key = d.isoformat()
                bucket = by_day.get(key, {"record_count": 0, "active_users": 0})
                points.append(
                    {
                        "date": key,
                        "record_count": bucket["record_count"],
                        "active_users": bucket["active_users"],
                    }
                )

            return {"days": days, "points": points}


admin_dashboard_service = AdminDashboardService()
