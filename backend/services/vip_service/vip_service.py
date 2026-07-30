from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.dao.vip_mapper import VipMapper
from backend.model.usage_record import UsageRecord
from backend.services.point_service.point_service import PointService, point_service


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PRACTICE_LIMITS = {"normal": 5, "vip": 20}
SUPPORTED_FEATURES = {"practice_generation", "detailed_analysis", "stage_report"}


class VipService:
    def __init__(
        self,
        mapper: VipMapper | None = None,
        points: PointService | None = None,
    ):
        self.mapper = mapper or VipMapper()
        self.points = points or point_service

    @staticmethod
    def _local_now(now: datetime | None = None) -> datetime:
        value = now or datetime.now(SHANGHAI_TZ)
        if value.tzinfo is None:
            return value
        return value.astimezone(SHANGHAI_TZ).replace(tzinfo=None)

    @staticmethod
    def _local_aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=SHANGHAI_TZ)
        return value.astimezone(SHANGHAI_TZ)

    async def _status(self, db: AsyncSession, user_id: int, now: datetime | None = None):
        local_now = self._local_now(now)
        info = await self.mapper.get_vip_info(db, user_id)
        is_vip = bool(info and info.expires_at and info.expires_at > local_now)
        return info, is_vip, local_now

    async def get_status(
        self,
        db: AsyncSession,
        user_id: int,
        now: datetime | None = None,
    ) -> dict:
        info, is_vip, _ = await self._status(db, user_id, now)
        return {
            "is_vip": is_vip,
            "started_at": self._local_aware(info.started_at) if info else None,
            "expires_at": self._local_aware(info.expires_at) if info else None,
        }

    async def check_entitlement(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        feature: str,
        now: datetime | None = None,
    ) -> dict:
        if feature not in SUPPORTED_FEATURES:
            raise BusinessError("INVALID_FEATURE", "不支持的权益类型", 400)
        _, is_vip, local_now = await self._status(db, user_id, now)
        membership = "vip" if is_vip else "normal"

        if feature != "practice_generation":
            if not is_vip:
                raise BusinessError("VIP_REQUIRED", "该功能需要VIP或积分兑换", 403)
            return {"allowed": True, "membership": membership, "remaining": None}

        limit = PRACTICE_LIMITS[membership]
        used = await self.mapper.count_usage(
            db,
            user_id,
            local_now.date(),
            feature,
            usage_source="quota",
        )
        if used < limit:
            return {"allowed": True, "membership": membership, "remaining": limit - used}

        count_credits = getattr(self.mapper, "count_available_extra_practices", None)
        available_credits = (
            await count_credits(db, user_id, local_now.date())
            if count_credits is not None
            else 0
        )
        if available_credits > 0:
            return {
                "allowed": True,
                "membership": membership,
                "remaining": available_credits,
                "usage_source": "points",
            }
        raise BusinessError(
            "USAGE_LIMIT_REACHED",
            "今日练习生成次数已用完，请使用积分兑换或开通VIP",
            403,
        )

    async def consume_usage(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        feature: str,
        request_id: str,
        usage_source: str = "quota",
        now: datetime | None = None,
    ) -> dict:
        if usage_source not in {"quota", "points"}:
            raise BusinessError("INVALID_USAGE_SOURCE", "不支持的次数来源", 400)
        existing = await self.mapper.get_usage_by_request_id(db, request_id)
        if existing is not None:
            if existing.user_id != user_id:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被使用", 409)
            return {"consumed": False, "reason": "duplicate"}

        await self.mapper.lock_user(db, user_id)
        local_now = self._local_now(now)
        if usage_source == "quota":
            entitlement = await self.check_entitlement(
                db, user_id=user_id, feature=feature, now=local_now
            )
            if entitlement.get("usage_source") == "points":
                usage_source = "points"
        else:
            if feature != "practice_generation":
                raise BusinessError("INVALID_USAGE_SOURCE", "积分次数仅用于额外练习", 400)
            entitlement = {"membership": "normal", "remaining": None}

        usage = UsageRecord(
            user_id=user_id,
            request_id=request_id,
            usage_date=local_now.date(),
            feature=feature,
            usage_source=usage_source,
        )
        self.mapper.add_usage(db, usage)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_usage_by_request_id(db, request_id)
            if existing is None or existing.user_id != user_id:
                raise
            return {"consumed": False, "reason": "duplicate"}
        remaining = entitlement["remaining"]
        return {
            "consumed": True,
            "reason": None,
            "remaining": None if remaining is None else remaining - 1,
        }

    async def get_usage(
        self,
        db: AsyncSession,
        user_id: int,
        now: datetime | None = None,
    ) -> dict:
        _, is_vip, local_now = await self._status(db, user_id, now)
        membership = "vip" if is_vip else "normal"
        practice_used = await self.mapper.count_usage(
            db,
            user_id,
            local_now.date(),
            "practice_generation",
            usage_source="quota",
        )
        points_used = await self.mapper.count_usage(
            db,
            user_id,
            local_now.date(),
            "practice_generation",
            usage_source="points",
        )
        count_exchanges = getattr(self.mapper, "count_extra_practice_exchanges", None)
        exchanged_count = (
            await count_exchanges(db, user_id, local_now.date())
            if count_exchanges is not None
            else points_used
        )
        practice_limit = PRACTICE_LIMITS[membership] + exchanged_count
        practice_used += points_used

        result = {
            "date": local_now.date(),
            "membership": membership,
            "practice_generation": {
                "used": practice_used,
                "limit": practice_limit,
                "remaining": max(practice_limit - practice_used, 0),
            },
        }
        for feature in ("detailed_analysis", "stage_report"):
            used = await self.mapper.count_usage(db, user_id, local_now.date(), feature)
            result[feature] = {
                "used": used,
                "limit": None if is_vip else 0,
                "remaining": None if is_vip else 0,
            }
        return result

    async def authorize_feature(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        feature: str,
        payment_method: str,
        request_id: str,
        now: datetime | None = None,
    ) -> dict:
        _, is_vip, _ = await self._status(db, user_id, now)
        if feature not in {"detailed_analysis", "stage_report"}:
            raise BusinessError("INVALID_FEATURE", "不支持的高级功能", 400)
        if is_vip:
            await self._record_feature_usage(
                db, user_id=user_id, feature=feature,
                request_id=request_id, usage_source="vip", now=now,
            )
            return {"allowed": True, "payment_method": "vip"}
        if payment_method != "points":
            raise BusinessError("VIP_REQUIRED", "该功能需要VIP或积分兑换", 403)
        await self.points.exchange(
            db,
            user_id=user_id,
            item_type=feature,
            target_id=None,
            request_id=request_id,
        )
        await self._record_feature_usage(
            db, user_id=user_id, feature=feature,
            request_id=request_id, usage_source="points", now=now,
        )
        return {"allowed": True, "payment_method": "points"}

    async def _record_feature_usage(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        feature: str,
        request_id: str,
        usage_source: str,
        now: datetime | None = None,
    ) -> None:
        existing = await self.mapper.get_usage_by_request_id(db, request_id)
        if existing is not None:
            if existing.user_id != user_id or existing.feature != feature:
                raise BusinessError("REQUEST_ID_CONFLICT", "请求编号已被其他权益使用", 409)
            return
        local_now = self._local_now(now)
        self.mapper.add_usage(db, UsageRecord(
            user_id=user_id,
            request_id=request_id,
            usage_date=local_now.date(),
            feature=feature,
            usage_source=usage_source,
        ))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.mapper.get_usage_by_request_id(db, request_id)
            if existing is None or existing.user_id != user_id or existing.feature != feature:
                raise


vip_service = VipService()
