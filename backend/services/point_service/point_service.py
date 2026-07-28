from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.dao.point_mapper import PointMapper
from backend.model.point_account import PointAccount
from backend.model.point_transaction import PointTransaction


EXCHANGE_COSTS = {
    "extra_practice": 10,
    "detailed_analysis": 10,
    "stage_report": 20,
}

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
REWARD_RULES = {
    "profile_completed": {"points": 10, "limit": 1, "daily": False, "description": "首次完善个人学习信息"},
    "daily_check_in": {"points": 2, "limit": 1, "daily": True, "description": "每日签到"},
    "practice_reward": {"points": 5, "limit": 3, "daily": True, "description": "完成有效练习"},
    "correction_reward": {"points": 3, "limit": 1, "daily": False, "description": "完成错题订正"},
    "streak_3_days": {"points": 10, "limit": 1, "daily": False, "description": "连续学习三天"},
}


class PointService:
    def __init__(self, mapper: PointMapper | None = None):
        self.mapper = mapper or PointMapper()

    @staticmethod
    def _account_data(account: PointAccount) -> dict:
        return {
            "balance": account.balance,
            "earned_total": account.earned_total,
            "spent_total": account.spent_total,
        }

    @staticmethod
    def _local_naive(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(SHANGHAI_TZ).replace(tzinfo=None)

    @staticmethod
    def _local_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=SHANGHAI_TZ)
        return value.astimezone(SHANGHAI_TZ)

    @classmethod
    def _day_bounds(cls, value: datetime) -> tuple[datetime, datetime]:
        local_value = cls._local_naive(value)
        started_at = datetime.combine(local_value.date(), time.min)
        return started_at, started_at + timedelta(days=1)

    async def get_account(self, db: AsyncSession, user_id: int) -> dict:
        try:
            account = await self.mapper.get_or_create_account(db, user_id)
            await db.commit()
        except IntegrityError:
            # Two first-time requests may race to create the same one-per-user account.
            await db.rollback()
            account = await self.mapper.get_account(db, user_id)
            if account is None:
                raise
        return self._account_data(account)

    async def change_points(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        amount: int,
        business_type: str,
        description: str,
        request_id: str,
    ) -> dict:
        if amount == 0:
            raise BusinessError("INVALID_POINT_CHANGE", "积分变动值不能为0", 400)

        existing = await self.mapper.get_transaction_by_request_id(db, request_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
            account = await self.mapper.get_account(db, user_id)
            if account is None:
                raise BusinessError("POINT_ACCOUNT_NOT_FOUND", "积分账户不存在", 500)
            return self._account_data(account)

        try:
            account = await self.mapper.get_or_create_account(db, user_id, for_update=True)
        except IntegrityError:
            # A concurrent first operation may have created the unique account.
            # Roll back the failed insert and continue against that account row.
            await db.rollback()
            existing = await self.mapper.get_transaction_by_request_id(db, request_id)
            if existing is not None:
                if existing.user_id != user_id:
                    raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
                account = await self.mapper.get_account(db, user_id)
                if account is None:
                    raise BusinessError("POINT_ACCOUNT_NOT_FOUND", "积分账户不存在", 500)
                return self._account_data(account)
            account = await self.mapper.get_account(db, user_id, for_update=True)
            if account is None:
                raise

        new_balance = account.balance + amount
        if new_balance < 0:
            raise BusinessError("INSUFFICIENT_POINTS", "积分不足", 400)

        account.balance = new_balance
        if amount > 0:
            account.earned_total += amount
        else:
            account.spent_total += -amount

        transaction = PointTransaction(
            user_id=user_id,
            account=account,
            request_id=request_id,
            business_type=business_type,
            change_amount=amount,
            balance_after=new_balance,
            description=description,
        )
        self.mapper.add_transaction(db, transaction)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_transaction_by_request_id(db, request_id)
            if existing is None or existing.user_id != user_id:
                raise
            account = await self.mapper.get_account(db, user_id)
            if account is None:
                raise BusinessError("POINT_ACCOUNT_NOT_FOUND", "积分账户不存在", 500)

        return self._account_data(account)

    async def reward(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request_id: str,
        occurred_at: datetime,
        business_type: str,
        business_id: str | None = None,
    ) -> dict:
        rule = REWARD_RULES[business_type]
        existing = await self.mapper.get_transaction_by_request_id(db, request_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
            return {"awarded": False, "reason": "duplicate", "points": 0}

        try:
            account = await self.mapper.get_or_create_account(db, user_id, for_update=True)
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_transaction_by_request_id(db, request_id)
            if existing is not None:
                if existing.user_id != user_id:
                    raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
                return {"awarded": False, "reason": "duplicate", "points": 0}
            account = await self.mapper.get_account(db, user_id, for_update=True)
            if account is None:
                raise
        started_at = ended_at = None
        if rule["daily"]:
            started_at, ended_at = self._day_bounds(occurred_at)

        count = await self.mapper.count_transactions(
            db,
            user_id,
            business_type,
            started_at=started_at,
            ended_at=ended_at,
            business_id=None if rule["daily"] else business_id,
        )
        if count >= rule["limit"]:
            await db.rollback()
            return {"awarded": False, "reason": "limit_reached", "points": 0}

        points = rule["points"]
        account.balance += points
        account.earned_total += points
        transaction = PointTransaction(
            user_id=user_id,
            account=account,
            request_id=request_id,
            business_type=business_type,
            business_id=business_id,
            change_amount=points,
            balance_after=account.balance,
            description=rule["description"],
            created_at=self._local_naive(occurred_at),
        )
        self.mapper.add_transaction(db, transaction)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_transaction_by_request_id(db, request_id)
            if existing is None:
                return {"awarded": False, "reason": "limit_reached", "points": 0}
            if existing.user_id != user_id:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
            return {"awarded": False, "reason": "duplicate", "points": 0}
        return {"awarded": True, "reason": None, "points": points, "balance": account.balance}

    async def reward_profile_completed(self, db: AsyncSession, event) -> dict:
        return await self.reward(
            db,
            user_id=event.user_id,
            request_id=event.request_id,
            occurred_at=event.occurred_at,
            business_type="profile_completed",
            business_id=str(event.user_id),
        )

    async def check_in(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        request_id: str,
        occurred_at: datetime | None = None,
    ) -> dict:
        return await self.reward(
            db,
            user_id=user_id,
            request_id=request_id,
            occurred_at=occurred_at or datetime.now(SHANGHAI_TZ),
            business_type="daily_check_in",
        )

    async def reward_practice(self, db: AsyncSession, event) -> dict:
        if not event.is_valid:
            return {"awarded": False, "reason": "invalid_practice", "points": 0}
        return await self.reward(
            db,
            user_id=event.user_id,
            request_id=event.request_id,
            occurred_at=event.occurred_at,
            business_type="practice_reward",
            business_id=str(event.practice_id),
        )

    async def reward_correction(self, db: AsyncSession, event) -> dict:
        if not event.first_success:
            return {"awarded": False, "reason": "not_first_success", "points": 0}
        return await self.reward(
            db,
            user_id=event.user_id,
            request_id=event.request_id,
            occurred_at=event.occurred_at,
            business_type="correction_reward",
            business_id=str(event.mistake_id),
        )

    async def reward_streak(self, db: AsyncSession, event) -> dict:
        return await self.reward(
            db,
            user_id=event.user_id,
            request_id=event.request_id,
            occurred_at=event.occurred_at,
            business_type="streak_3_days",
            business_id=event.streak_id,
        )

    async def reward_streak_if_eligible(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        occurred_at: datetime,
    ) -> dict:
        """每连续学习满 3 天奖励一次；同一连续周期的里程碑可幂等重试。"""
        local_day = self._local_aware(occurred_at).date()
        learning_times = await self.mapper.list_recent_learning_times(db, user_id)
        learning_days = {
            self._local_aware(value).date()
            for value in learning_times
            if value is not None and self._local_aware(value).date() <= local_day
        }
        if local_day not in learning_days:
            return {"awarded": False, "reason": "no_learning_today", "points": 0}

        streak_days = 0
        cursor = local_day
        while cursor in learning_days:
            streak_days += 1
            cursor -= timedelta(days=1)

        if streak_days < 3 or streak_days % 3:
            return {"awarded": False, "reason": "streak_not_reached", "points": 0}

        streak_start = local_day - timedelta(days=streak_days - 1)
        milestone = streak_days // 3
        streak_id = f"{streak_start.isoformat()}:{milestone}"
        return await self.reward(
            db,
            user_id=user_id,
            request_id=f"streak:{user_id}:{streak_id}",
            occurred_at=occurred_at,
            business_type="streak_3_days",
            business_id=streak_id,
        )

    async def get_tasks(self, db: AsyncSession, user_id: int, now: datetime | None = None) -> dict:
        now = now or datetime.now(SHANGHAI_TZ)
        started_at, ended_at = self._day_bounds(now)
        definitions = (
            ("daily_check_in", "每日签到", 1, 2),
            ("practice_reward", "完成有效练习", 3, 5),
            ("correction_reward", "完成错题订正", 1, 3),
            ("streak_3_days", "连续学习三天", 1, 10),
        )
        progress_by_type = await self.mapper.count_transactions_by_type(
            db,
            user_id,
            started_at=started_at,
            ended_at=ended_at,
        )

        # 计算连续学习天数
        streak_days = 0
        try:
            learning_times = await self.mapper.list_recent_learning_times(db, user_id)
            learning_days = {
                self._local_aware(value).date()
                for value in learning_times
                if value is not None
            }
            local_day = self._local_aware(now).date()
            if local_day in learning_days:
                cursor = local_day
                while cursor in learning_days:
                    streak_days += 1
                    cursor -= timedelta(days=1)
        except Exception:
            pass

        items = []
        for task_type, title, target, reward_points in definitions:
            if task_type == "streak_3_days":
                # 连续学习三天任务：显示连续天数/3
                progress = min(streak_days, 3)
                target = 3
            else:
                progress = progress_by_type.get(task_type, 0)
                progress = min(progress, target)
            items.append(
                {
                    "task_type": task_type,
                    "title": title,
                    "progress": progress,
                    "target": target,
                    "reward_points": reward_points,
                    "claimed": progress >= target,
                }
            )
        return {"date": started_at.date(), "items": items}

    async def exchange(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        item_type: str,
        target_id: int | None,
        request_id: str,
    ) -> dict:
        cost = EXCHANGE_COSTS.get(item_type)
        if cost is None:
            raise BusinessError("INVALID_EXCHANGE_ITEM", "不支持的积分兑换项目", 400)

        account = await self.change_points(
            db,
            user_id=user_id,
            amount=-cost,
            business_type=f"exchange_{item_type}",
            description=f"积分兑换：{item_type}",
            request_id=request_id,
        )
        return {
            "item_type": item_type,
            "target_id": target_id,
            "cost": cost,
            "balance": account["balance"],
        }

    async def list_transactions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        page: int,
        page_size: int,
    ) -> dict:
        transactions, total = await self.mapper.list_transactions(
            db, user_id, page, page_size
        )
        return {
            "items": [
                {
                    "transaction_id": transaction.id,
                    "business_type": transaction.business_type,
                    "change": transaction.change_amount,
                    "balance_after": transaction.balance_after,
                    "description": transaction.description,
                    "created_at": self._local_aware(transaction.created_at),
                }
                for transaction in transactions
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }


point_service = PointService()
