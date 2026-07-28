"""成员四：学习记录、推荐、每日计划、站内提醒 Service"""

import uuid
from datetime import date, datetime, timedelta
from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, and_, case, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.core.exceptions import BusinessError
from backend.middleware.logging import get_logger
from backend.model import AsyncSessionLocal
from backend.model.learning_models import (
    LearningRecord, DailyPlan, Notification
)
from backend.model.user_profile import UserProfile
from backend.model.vip_info import VipInfo
from backend.model.mastery import AnswerRecord, Mistake, ReviewPlan

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
            if subject == "__unclassified__":
                conditions.append(
                    (LearningRecord.subject.is_(None)) | (LearningRecord.subject == "")
                )
            elif subject:
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

    async def list_record_subjects(self, user_id: int) -> List[str]:
        """Return all non-empty subject snapshots represented in learning records."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(LearningRecord.subject)
                .where(
                    LearningRecord.user_id == user_id,
                    LearningRecord.subject.is_not(None),
                    LearningRecord.subject != '',
                )
                .distinct()
                .order_by(LearningRecord.subject)
            )
            return list((await session.execute(stmt)).scalars().all())

    async def has_unclassified_records(self, user_id: int) -> bool:
        """Whether legacy records without a trustworthy subject snapshot exist."""
        async with AsyncSessionLocal() as session:
            stmt = select(LearningRecord.id).where(
                LearningRecord.user_id == user_id,
                (LearningRecord.subject.is_(None)) | (LearningRecord.subject == ""),
            ).limit(1)
            return (await session.execute(stmt)).scalar_one_or_none() is not None

    async def get_stats_summary(self, user_id: int) -> Dict:
        """获取学习统计摘要（用于学习记录页顶部卡片）"""
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(
                        func.sum(
                            case(
                                (
                                    LearningRecord.record_type.in_(("practice", "correction")),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        func.sum(LearningRecord.question_count),
                        func.avg(LearningRecord.accuracy),
                        func.sum(LearningRecord.mastery_change),
                    ).where(LearningRecord.user_id == user_id)
                )
            ).one()
            practice_count = row[0] or 0
            question_count = row[1] or 0
            avg_accuracy = row[2]
            avg_accuracy = round(float(avg_accuracy), 1) if avg_accuracy else 0.0
            mastery_change = row[3] or 0

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
                subject=event.subject,
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
        secondary: List[Dict] = []

        # 优先级 1：今日到期的错题复习
        review_due = await self._get_review_due_recommendation(user_id, today)
        low_mastery_list = await self._get_low_mastery_list(user_id)
        primary = review_due or (low_mastery_list[0] if low_mastery_list else None)

        # 优先级 2 的其它项进入 secondary
        for item in low_mastery_list[:3]:
            if item is primary:
                continue
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
                    SELECT m.id, m.knowledge_point_name, COUNT(*) as cnt, m.subject
                    FROM mistake m
                    INNER JOIN review_plan rp ON rp.mistake_id = m.id
                    WHERE m.user_id = :uid
                      AND rp.review_date = :today
                      AND rp.status = 'pending'
                    GROUP BY m.id, m.knowledge_point_name, m.subject
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
                        "knowledge_point_name": row[1],
                        "subject": row[3],
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
                    SELECT km.id, km.knowledge_point_name, km.mastery_score,
                           km.answer_count, km.correct_count,
                           (
                               SELECT ar.subject
                               FROM answer_record ar
                               WHERE ar.user_id = km.user_id
                                 AND ar.knowledge_point_name = km.knowledge_point_name
                                 AND ar.subject IS NOT NULL
                                 AND ar.subject <> ''
                               ORDER BY ar.created_at DESC
                               LIMIT 1
                           ) AS subject
                    FROM knowledge_mastery km
                    WHERE km.user_id = :uid
                      AND km.mastery_score < 60
                      AND km.answer_count > 0
                    ORDER BY km.mastery_score ASC, km.last_studied_at DESC
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
                        "description": (
                            f"「{row[1]}」历史答题 {row[4]}/{row[3]}，"
                            f"知识点掌握度 {row[2]}%；"
                            + (
                                "在当前薄弱知识点中掌握度最低，因此建议优先巩固"
                                if i == 0 else "仍低于 60%，建议继续巩固"
                            )
                        ),
                        "selection_reason": "lowest_mastery" if i == 0 else "low_mastery",
                        "target_id": row[0],
                        "knowledge_point_name": row[1],
                        "subject": row[5],
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
                        "training_scope": "daily_subject",
                        "priority": 3,
                    }]

                subject = (profile.subject or "学科")
                # 优先把“今日练习”落实为近期该学科表现较弱的具体知识点。
                # 若没有历史记录，前端会退回当前年级、当前学科的随机巩固。
                recent_focus = (
                    await session.execute(
                        select(
                            AnswerRecord.knowledge_point_name,
                            func.avg(
                                case(
                                    (AnswerRecord.is_correct.is_(True), 1.0),
                                    else_=0.0,
                                )
                            ).label("accuracy"),
                            func.max(AnswerRecord.created_at).label("last_answered_at"),
                        )
                        .where(
                            AnswerRecord.user_id == user_id,
                            AnswerRecord.subject == subject,
                            AnswerRecord.knowledge_point_name.isnot(None),
                            AnswerRecord.knowledge_point_name != "",
                            AnswerRecord.knowledge_point_name.notin_(
                                ["综合知识点", "其他", "未知知识点", "随机巩固"]
                            ),
                            ~AnswerRecord.knowledge_point_name.like("%随机巩固%"),
                        )
                        .group_by(AnswerRecord.knowledge_point_name)
                        .order_by(
                            text("accuracy ASC"),
                            text("last_answered_at DESC"),
                        )
                        .limit(1)
                    )
                ).first()

                return [{
                    "type": "practice",
                    "title": f"开始今日{subject}练习",
                    "description": (
                        f"根据近期记录，优先训练「{recent_focus.knowledge_point_name}」"
                        if recent_focus
                        else f"暂无可用历史记录，将自动安排{profile.grade or ''}{subject}巩固训练"
                    ),
                    "target_id": None,
                    "knowledge_point_name": (
                        recent_focus.knowledge_point_name if recent_focus else None
                    ),
                    "subject": subject,
                    "training_scope": "recent_weakness" if recent_focus else "daily_subject",
                    "priority": 3,
                }]
        except Exception as e:
            logger.warning("Goal recommendation failed: %s", e)
            return [{
                "type": "practice",
                "title": "开始今日练习",
                "description": "完成一组练习保持学习节奏",
                "target_id": None,
                "training_scope": "daily_subject",
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

            pending_corrections = await self._get_pending_correction_count(user_id, today)
            tasks = self._build_plan_tasks(plan, pending_corrections)
            task_completed = sum(1 for task in tasks if task["status"] == "completed")
            completed = task_completed == len(tasks)

            return {
                "date": today.isoformat(),
                "target_groups": plan.target_groups,
                "completed_groups": plan.completed_groups,
                "completed": completed,
                "task_completed": task_completed,
                "task_total": len(tasks),
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

    async def _get_pending_correction_count(self, user_id: int, today: date) -> int:
        """待订正错题和已到期复习都属于今日错题任务。"""
        async with AsyncSessionLocal() as session:
            mistake_count = (
                await session.execute(
                    select(func.count(Mistake.id)).where(
                        Mistake.user_id == user_id,
                        Mistake.correction_status.in_(("pending", "review_due")),
                    )
                )
            ).scalar() or 0
            review_count = (
                await session.execute(
                    select(func.count(ReviewPlan.id)).where(
                        ReviewPlan.user_id == user_id,
                        ReviewPlan.status == "pending",
                        ReviewPlan.review_date <= today,
                    )
                )
            ).scalar() or 0
            return int(mistake_count) + int(review_count)

    def _build_plan_tasks(
        self, plan: DailyPlan, pending_corrections: int = 0
    ) -> List[Dict]:
        """根据计划生成今日任务列表"""
        tasks = []
        remaining = plan.target_groups - plan.completed_groups

        if remaining > 0:
            tasks.append({
                "task_type": "practice",
                "title": f"完成 {remaining} 组推荐练习",
                "status": "pending",
                "reward_points": 5,
            })
        else:
            tasks.append({
                "task_type": "practice",
                "title": "今日练习目标已完成",
                "status": "completed",
                "reward_points": 5,
            })
        if pending_corrections:
            tasks.append({
                "task_type": "correction",
                "title": f"完成 {pending_corrections} 道待订正或到期错题",
                "status": "pending",
                "reward_points": 3,
            })
        return tasks

    # ─── 站内提醒 ──────────────────────────────────────

    async def get_notifications(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict], int, int]:
        """分页查询站内提醒"""
        await self.generate_daily_notifications(user_id)
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
        await self.generate_daily_notifications(user_id)
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
        self,
        user_id: int,
        n_type: str,
        title: str,
        content: Optional[str] = None,
        dedupe_key: Optional[str] = None,
    ) -> Optional[int]:
        """创建站内提醒；传入 dedupe_key 时重复请求安全返回。"""
        async with AsyncSessionLocal() as session:
            n = Notification(
                user_id=user_id,
                type=n_type,
                title=title,
                content=content,
                dedupe_key=dedupe_key,
            )
            session.add(n)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return None
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
                    WHERE m.user_id = :uid AND rp.review_date <= :today AND rp.status = 'pending'
                    """
                )
                result = await session.execute(sql, {"uid": user_id, "today": today})
                count = result.scalar() or 0
                if count > 0:
                    await self.create_notification(
                        user_id, "review_due",
                        f"今日有 {count} 道错题需要复习",
                        "打开学习首页查看复习计划",
                        dedupe_key=f"review_due:{today.isoformat()}",
                    )
        except Exception as exc:
            logger.warning("Generate review reminder failed for user=%s: %s", user_id, exc)

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
                        dedupe_key=f"daily_plan:{today.isoformat()}",
                    )
                elif any(
                    task["task_type"] == "correction" and task["status"] != "completed"
                    for task in plan.get("tasks", [])
                ):
                    await self.create_notification(
                        user_id,
                        "daily_plan",
                        "今日还有错题订正或复习任务未完成",
                        "完成错题任务后才算完成今日学习计划",
                        dedupe_key=f"daily_plan:{today.isoformat()}",
                    )
        except Exception as exc:
            logger.warning("Generate daily-plan reminder failed for user=%s: %s", user_id, exc)

        # 到期前 3 天开始提醒，每天最多生成一条。
        try:
            async with AsyncSessionLocal() as session:
                vip = (
                    await session.execute(
                        select(VipInfo).where(VipInfo.user_id == user_id).limit(1)
                    )
                ).scalar_one_or_none()
                if vip and vip.expires_at:
                    expires_at = vip.expires_at
                    expires_date = expires_at.date()
                    days_left = (expires_date - today).days
                    if 0 <= days_left <= 3:
                        await self.create_notification(
                            user_id,
                            "vip_expiring",
                            f"会员将在 {days_left} 天后到期" if days_left else "会员将在今天到期",
                            f"会员有效期至 {expires_date.isoformat()}，续费后可继续使用会员权益",
                            dedupe_key=f"vip_expiring:{today.isoformat()}",
                        )
        except Exception as exc:
            logger.warning("Generate VIP reminder failed for user=%s: %s", user_id, exc)


# 全局单例
record_service = RecordService()
