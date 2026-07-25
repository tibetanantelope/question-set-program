"""成员四：学习记录、推荐、每日计划、站内提醒 Service"""

import uuid
from datetime import date, datetime, timedelta
from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger
from backend.model import AsyncSessionLocal
from backend.model.learning_models import (
    LearningRecord, DailyPlan, Notification
)
from backend.model.user_profile import UserProfile

logger = get_logger(__name__)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _today() -> date:
    return datetime.now(SHANGHAI).date()


def _now() -> datetime:
    return datetime.now(SHANGHAI)


class RecordService:
    """学习记录、推荐、每日计划、站内提醒服务"""

    # ─── 学习记录 ──────────────────────────────────────

    async def get_records(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        record_type: Optional[str] = None,
        subject: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Tuple[List[Dict], int, int]:
        """分页查询历史学习记录"""
        async with AsyncSessionLocal() as session:
            conditions = [LearningRecord.user_id == user_id]

            if record_type:
                conditions.append(LearningRecord.record_type == record_type)
            if subject:
                conditions.append(LearningRecord.subject == subject)
            if date_from:
                conditions.append(LearningRecord.occurred_at >= f"{date_from} 00:00:00")
            if date_to:
                conditions.append(LearningRecord.occurred_at <= f"{date_to} 23:59:59")

            # 总数
            count_q = select(func.count()).select_from(LearningRecord).where(and_(*conditions))
            total = (await session.execute(count_q)).scalar() or 0

            # 分页
            offset = (page - 1) * page_size
            q = (
                select(LearningRecord)
                .where(and_(*conditions))
                .order_by(LearningRecord.occurred_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            rows = (await session.execute(q)).scalars().all()

            items = [
                {
                    "record_id": r.id,
                    "record_type": r.record_type,
                    "title": r.title,
                    "subject": r.subject,
                    "knowledge_point_name": r.knowledge_point_name,
                    "question_count": r.question_count,
                    "correct_count": r.correct_count,
                    "accuracy": float(r.accuracy) if r.accuracy is not None else None,
                    "mastery_change": r.mastery_change,
                    "occurred_at": r.occurred_at.isoformat() if r.occurred_at else "",
                }
                for r in rows
            ]
            pages = ceil(total / page_size) if total else 0
            return items, total, pages

    async def get_stats_summary(self, user_id: int) -> Dict:
        """获取学习统计摘要（用于学习记录页顶部卡片）"""
        async with AsyncSessionLocal() as session:
            # 练习组数
            practice_q = select(func.count()).select_from(LearningRecord).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.record_type.in_(['practice', 'correction']),
                )
            )
            practice_count = (await session.execute(practice_q)).scalar() or 0

            # 总题数
            question_q = select(func.sum(LearningRecord.question_count)).where(
                LearningRecord.user_id == user_id
            )
            question_count = (await session.execute(question_q)).scalar() or 0

            # 平均正确率
            accuracy_q = select(func.avg(LearningRecord.accuracy)).where(
                and_(
                    LearningRecord.user_id == user_id,
                    LearningRecord.accuracy.isnot(None),
                )
            )
            avg_accuracy = (await session.execute(accuracy_q)).scalar()
            avg_accuracy = round(float(avg_accuracy), 1) if avg_accuracy else 0.0

            # 掌握度变化总和
            mastery_q = select(func.sum(LearningRecord.mastery_change)).where(
                LearningRecord.user_id == user_id
            )
            mastery_change = (await session.execute(mastery_q)).scalar() or 0

            return {
                "practice_count": practice_count,
                "question_count": question_count,
                "avg_accuracy": avg_accuracy,
                "mastery_change": mastery_change,
            }

    async def record_practice(self, event: Any) -> Optional[int]:
        """记录一条练习完成记录（幂等）"""
        if not event.is_valid:
            return None

        async with AsyncSessionLocal() as session:
            return await self._insert_record(
                session,
                user_id=event.user_id,
                record_type="practice",
                title=f"{event.knowledge_point_name or event.subject or '专项练习'}",
                subject=event.subject,
                knowledge_point_name=event.knowledge_point_name,
                question_count=event.question_count,
                correct_count=event.correct_count,
                accuracy=event.accuracy,
                request_id=event.request_id,
                occurred_at=event.completed_at or _now(),
            )

    async def record_correction(self, event: Any) -> Optional[int]:
        """记录一条错题订正记录（幂等）"""
        async with AsyncSessionLocal() as session:
            return await self._insert_record(
                session,
                user_id=event.user_id,
                record_type="correction",
                title=f"错题订正 - {event.knowledge_point_name or '知识点'}",
                knowledge_point_name=event.knowledge_point_name,
                question_count=1,
                correct_count=1 if event.first_success else 0,
                accuracy=100.0 if event.first_success else 0.0,
                request_id=event.request_id,
                occurred_at=event.completed_at or _now(),
            )

    async def _insert_record(
        self,
        session: AsyncSession,
        user_id: int,
        record_type: str,
        title: str,
        subject: Optional[str] = None,
        knowledge_point_name: Optional[str] = None,
        question_count: int = 0,
        correct_count: int = 0,
        accuracy: Optional[float] = None,
        mastery_change: int = 0,
        request_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Optional[int]:
        """幂等插入学习记录"""
        if request_id:
            existing = await session.execute(
                select(LearningRecord).where(LearningRecord.request_id == request_id)
            )
            if existing.scalar_one_or_none():
                logger.info("Record already exists for request_id=%s, skip", request_id)
                return None

        record = LearningRecord(
            user_id=user_id,
            record_type=record_type,
            title=title,
            subject=subject,
            knowledge_point_name=knowledge_point_name,
            question_count=question_count,
            correct_count=correct_count,
            accuracy=accuracy,
            mastery_change=mastery_change,
            request_id=request_id or str(uuid.uuid4()),
            occurred_at=occurred_at or _now(),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        logger.info("Created learning record %s for user %s", record.id, user_id)
        return record.id

    # ─── 首页推荐 ──────────────────────────────────────

    async def get_home_recommendations(self, user_id: int) -> Dict:
        """获取首页主要推荐 + 次要推荐"""
        today = _today()
        primary = None
        secondary: List[Dict] = []

        # 优先级 1：今日到期的错题复习
        primary = await self._get_review_due_recommendation(user_id, today)

        # 优先级 2：低掌握度且近期学过的知识点
        if not primary:
            primary = await self._get_low_mastery_recommendation(user_id)

        # 优先级 2 的其它项进入 secondary
        low_mastery_list = await self._get_low_mastery_list(user_id)
        for item in low_mastery_list[:3]:
            secondary.append(item)

        # 优先级 3：学习目标相关内容
        goal_items = await self._get_goal_recommendations(user_id)
        for item in goal_items[:2]:
            secondary.append(item)

        return {
            "primary": primary,
            "secondary": secondary,
        }

    async def _get_review_due_recommendation(self, user_id: int, today: date) -> Optional[Dict]:
        """查询今日到期复习错题"""
        try:
            async with AsyncSessionLocal() as session:
                sql = text(
                    """
                    SELECT m.id, m.knowledge_point_name, COUNT(*) as cnt
                    FROM mistake m
                    INNER JOIN review_plan rp ON rp.mistake_id = m.id
                    WHERE m.user_id = :uid
                      AND rp.review_date = :today
                      AND rp.is_completed = 0
                    GROUP BY m.id, m.knowledge_point_name
                    LIMIT 1
                    """
                )
                result = await session.execute(sql, {"uid": user_id, "today": today})
                row = result.fetchone()
                if row:
                    return {
                        "type": "review",
                        "title": f"复习{row[1] or '历史'}错题",
                        "description": f"有 {row[2]} 道错题今日到期",
                        "target_id": row[0],
                        "priority": 1,
                    }
        except Exception as e:
            logger.warning("Review due query failed (member 3 tables may not exist): %s", e)

        return None

    async def _get_low_mastery_recommendation(self, user_id: int) -> Optional[Dict]:
        """查询低掌握度且近期学过的知识点"""
        items = await self._get_low_mastery_list(user_id)
        return items[0] if items else None

    async def _get_low_mastery_list(self, user_id: int) -> List[Dict]:
        """获取低掌握度知识点列表"""
        try:
            async with AsyncSessionLocal() as session:
                sql = text(
                    """
                    SELECT km.id, km.knowledge_point_name, km.mastery_score
                    FROM knowledge_mastery km
                    WHERE km.user_id = :uid
                      AND km.mastery_score < 60
                    ORDER BY km.last_studied_at DESC
                    LIMIT 5
                    """
                )
                result = await session.execute(sql, {"uid": user_id})
                rows = result.fetchall()
                items = []
                for i, row in enumerate(rows):
                    items.append({
                        "type": "practice",
                        "title": f"巩固{row[1]}",
                        "description": f"当前掌握度 {row[2]}，建议加强练习",
                        "target_id": row[0],
                        "priority": 2,
                    })
                return items
        except Exception as e:
            logger.warning("Low mastery query failed: %s", e)
            return await self._fallback_low_mastery(user_id)

    async def _fallback_low_mastery(self, user_id: int) -> List[Dict]:
        """降级方案：从 learning_record 中推断薄弱知识点"""
        try:
            async with AsyncSessionLocal() as session:
                q = (
                    select(
                        LearningRecord.knowledge_point_name,
                        func.count().label('cnt'),
                        func.avg(LearningRecord.accuracy).label('avg_acc'),
                    )
                    .where(
                        and_(
                            LearningRecord.user_id == user_id,
                            LearningRecord.knowledge_point_name.isnot(None),
                            LearningRecord.accuracy.isnot(None),
                        )
                    )
                    .group_by(LearningRecord.knowledge_point_name)
                    .order_by(func.avg(LearningRecord.accuracy))
                    .limit(3)
                )
                rows = (await session.execute(q)).all()
                items = []
                for row in rows:
                    avg_acc = float(row.avg_acc) if row.avg_acc else 0
                    items.append({
                        "type": "practice",
                        "title": f"巩固{row.knowledge_point_name}",
                        "description": f"历史正确率约 {avg_acc:.0f}%，建议加强练习",
                        "target_id": None,
                        "priority": 2,
                    })
                return items
        except Exception:
            return []

    async def _get_goal_recommendations(self, user_id: int) -> List[Dict]:
        """根据学习目标生成推荐（使用 ORM 查询 UserProfile）"""
        try:
            async with AsyncSessionLocal() as session:
                q = select(UserProfile).where(UserProfile.user_id == user_id).limit(1)
                result = await session.execute(q)
                profile = result.scalar_one_or_none()

                if not profile:
                    return [{
                        "type": "practice",
                        "title": "开始今日练习",
                        "description": "完成一组练习保持学习节奏",
                        "target_id": None,
                        "priority": 3,
                    }]

                goal_map = {
                    "daily": "日常巩固",
                    "weakness": "薄弱点补习",
                    "exam": "考试复习",
                }
                goal = (profile.learning_goal or "daily")
                subject = (profile.subject or "学科")

                items = []
                if goal in ("weakness", "daily"):
                    items.append({
                        "type": "practice",
                        "title": f"{subject}薄弱点专项练习",
                        "description": f"基于「{goal_map.get(goal, '日常巩固')}」目标推荐",
                        "target_id": None,
                        "priority": 3,
                    })
                elif goal == "exam":
                    items.append({
                        "type": "practice",
                        "title": f"{subject}考试复习综合练习",
                        "description": "基于「考试复习」目标推荐",
                        "target_id": None,
                        "priority": 3,
                    })
                if not items:
                    items.append({
                        "type": "practice",
                        "title": "开始今日练习",
                        "description": "完成一组练习保持学习节奏",
                        "target_id": None,
                        "priority": 3,
                    })
                return items
        except Exception as e:
            logger.warning("Goal recommendation failed: %s", e)
            return [{
                "type": "practice",
                "title": "开始今日练习",
                "description": "完成一组练习保持学习节奏",
                "target_id": None,
                "priority": 3,
            }]

    # ─── 每日计划 ──────────────────────────────────────

    async def get_today_plan(self, user_id: int) -> Dict:
        """获取今日计划，不存在则自动创建"""
        today = _today()

        target = await self._get_user_target_groups(user_id)

        async with AsyncSessionLocal() as session:
            q = select(DailyPlan).where(
                and_(DailyPlan.user_id == user_id, DailyPlan.plan_date == today)
            )
            plan = (await session.execute(q)).scalar_one_or_none()

            if not plan:
                plan = DailyPlan(
                    user_id=user_id,
                    plan_date=today,
                    target_groups=target,
                    completed_groups=0,
                    is_completed=0,
                )
                session.add(plan)
                await session.commit()
                await session.refresh(plan)

            tasks = self._build_plan_tasks(plan)

            return {
                "date": today.isoformat(),
                "target_groups": plan.target_groups,
                "completed_groups": plan.completed_groups,
                "completed": bool(plan.is_completed),
                "tasks": tasks,
            }

    async def update_plan_progress(self, event: Any) -> None:
        """完成练习后更新今日进度（幂等）"""
        if not event.is_valid:
            return

        today = _today()
        async with AsyncSessionLocal() as session:
            q = select(DailyPlan).where(
                and_(DailyPlan.user_id == event.user_id, DailyPlan.plan_date == today)
            )
            plan = (await session.execute(q)).scalar_one_or_none()
            if not plan:
                target = await self._get_user_target_groups(event.user_id)
                plan = DailyPlan(
                    user_id=event.user_id,
                    plan_date=today,
                    target_groups=target,
                    completed_groups=1,
                )
                session.add(plan)
            else:
                plan.completed_groups = min(plan.completed_groups + 1, plan.target_groups)

            plan.is_completed = 1 if plan.completed_groups >= plan.target_groups else 0
            await session.commit()
            logger.info(
                "Plan progress updated: user=%s completed=%s/%s",
                event.user_id, plan.completed_groups, plan.target_groups,
            )

    async def _get_user_target_groups(self, user_id: int) -> int:
        """从用户画像获取每日目标组数（使用 ORM 查询）"""
        try:
            async with AsyncSessionLocal() as session:
                q = select(UserProfile).where(UserProfile.user_id == user_id).limit(1)
                result = await session.execute(q)
                profile = result.scalar_one_or_none()
                if profile and profile.daily_target_groups:
                    return int(profile.daily_target_groups)
        except Exception:
            pass
        return 3  # 默认值

    def _build_plan_tasks(self, plan: DailyPlan) -> List[Dict]:
        """根据计划生成今日任务列表"""
        tasks = []
        remaining = plan.target_groups - plan.completed_groups

        if remaining > 0:
            tasks.append({
                "task_type": "practice",
                "title": f"完成 {remaining} 组推荐练习",
                "status": "pending",
            })
        else:
            tasks.append({
                "task_type": "practice",
                "title": "今日练习目标已完成",
                "status": "completed",
            })
        tasks.append({
            "task_type": "correction",
            "title": "检查到期错题并完成订正",
            "status": "pending",
        })
        return tasks

    # ─── 站内提醒 ──────────────────────────────────────

    async def get_notifications(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict], int, int]:
        """分页查询站内提醒"""
        async with AsyncSessionLocal() as session:
            conditions = [Notification.user_id == user_id]
            count_q = select(func.count()).select_from(Notification).where(and_(*conditions))
            total = (await session.execute(count_q)).scalar() or 0

            offset = (page - 1) * page_size
            q = (
                select(Notification)
                .where(and_(*conditions))
                .order_by(Notification.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            rows = (await session.execute(q)).scalars().all()

            items = [
                {
                    "notification_id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "is_read": bool(n.is_read),
                    "created_at": n.created_at.isoformat() if n.created_at else "",
                }
                for n in rows
            ]
            pages = ceil(total / page_size) if total else 0
            return items, total, pages

    async def get_unread_count(self, user_id: int) -> int:
        """获取未读通知数量"""
        async with AsyncSessionLocal() as session:
            q = select(func.count()).select_from(Notification).where(
                and_(Notification.user_id == user_id, Notification.is_read == 0)
            )
            result = await session.execute(q)
            return result.scalar() or 0

    async def mark_notification_read(self, user_id: int, notification_id: int) -> bool:
        """标记提醒已读"""
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(
                and_(Notification.id == notification_id, Notification.user_id == user_id)
            )
            n = (await session.execute(q)).scalar_one_or_none()
            if not n:
                raise BusinessError("NOTIFICATION_NOT_FOUND", "提醒不存在", 404)
            n.is_read = 1
            await session.commit()
            return True

    async def mark_all_notifications_read(self, user_id: int) -> int:
        """批量标记所有提醒已读，返回更新条数"""
        async with AsyncSessionLocal() as session:
            q = select(Notification).where(
                and_(Notification.user_id == user_id, Notification.is_read == 0)
            )
            result = await session.execute(q)
            notifications = result.scalars().all()
            count = 0
            for n in notifications:
                n.is_read = 1
                count += 1
            if count > 0:
                await session.commit()
            return count

    async def create_notification(
        self, user_id: int, n_type: str, title: str, content: Optional[str] = None
    ) -> int:
        """创建站内提醒"""
        async with AsyncSessionLocal() as session:
            n = Notification(
                user_id=user_id,
                type=n_type,
                title=title,
                content=content,
            )
            session.add(n)
            await session.commit()
            await session.refresh(n)
            return n.id

    async def generate_daily_notifications(self, user_id: int) -> None:
        """每日自动生成提醒（可配合定时任务）"""
        today = _today()

        # 检查是否有今日到期复习
        try:
            async with AsyncSessionLocal() as session:
                sql = text(
                    """
                    SELECT COUNT(*) FROM mistake m
                    INNER JOIN review_plan rp ON rp.mistake_id = m.id
                    WHERE m.user_id = :uid AND rp.review_date = :today AND rp.is_completed = 0
                    """
                )
                result = await session.execute(sql, {"uid": user_id, "today": today})
                count = result.scalar() or 0
                if count > 0:
                    await self.create_notification(
                        user_id, "review_due",
                        f"今日有 {count} 道错题需要复习",
                        "打开学习首页查看复习计划",
                    )
        except Exception:
            pass

        # 检查每日计划是否完成
        try:
            plan = await self.get_today_plan(user_id)
            if not plan.get("completed", False) and plan.get("target_groups", 0) > 0:
                remaining = plan["target_groups"] - plan["completed_groups"]
                if remaining > 0:
                    await self.create_notification(
                        user_id, "daily_plan",
                        f"今日还剩 {remaining} 组练习未完成",
                        "继续完成每日学习目标",
                    )
        except Exception:
            pass


# 全局单例
record_service = RecordService()
