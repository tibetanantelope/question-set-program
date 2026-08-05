"""管理员服务：用户管理 + 操作审计。"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.model.user import User, AdminAudit
from backend.dao.user_profile_mapper import UserProfileMapper
from backend.model import AsyncSessionLocal


class AdminService:
    # ── 用户管理 ──────────────────────────────────────

    async def list_users(
        self,
        keyword: str | None = None,
        role: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        async with AsyncSessionLocal() as db:
            conditions = []
            if keyword:
                like = f"%{keyword}%"
                conditions.append(or_(User.username.like(like), User.id == _safe_int(keyword)))
            if role:
                conditions.append(User.role == role)
            if status:
                conditions.append(User.status == status)

            base = select(User)
            if conditions:
                base = base.where(*conditions)
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await db.execute(count_stmt)).scalar() or 0

            query = base.order_by(desc(User.id)).offset(offset).limit(page_size)
            rows = (await db.execute(query)).scalars().all()

            profiles = {}
            if rows:
                mapper = UserProfileMapper(AsyncSessionLocal)
                for u in rows:
                    p = await mapper.get_by_user_id(u.id)
                    profiles[u.id] = p

            items = []
            for u in rows:
                p = profiles.get(u.id)
                items.append({
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "status": u.status,
                    "stage": p.stage if p else None,
                    "grade": p.grade if p else None,
                    "subject": p.subject if p else None,
                    "diagnostic_status": p.diagnostic_status if p else None,
                })

            pages = (total + page_size - 1) // page_size
            return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": pages}

    async def get_user_detail(self, user_id: int) -> dict:
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not u:
                raise BusinessError("USER_NOT_FOUND", "用户不存在", 404)
            mapper = UserProfileMapper(AsyncSessionLocal)
            p = await mapper.get_by_user_id(user_id)
            return {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "status": u.status,
                "profile": {
                    "stage": p.stage if p else None,
                    "grade": p.grade if p else None,
                    "subject": p.subject if p else None,
                    "learning_goal": p.learning_goal if p else None,
                    "weekly_study_days": p.weekly_study_days if p else None,
                    "daily_target_groups": p.daily_target_groups if p else None,
                    "diagnostic_status": p.diagnostic_status if p else None,
                } if p else None,
            }

    async def disable_user(self, user_id: int, admin: User, ip: str | None = None) -> dict:
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not u:
                raise BusinessError("USER_NOT_FOUND", "用户不存在", 404)
            if u.role == "admin":
                raise BusinessError("CANNOT_DISABLE_ADMIN", "不能禁用管理员账号", 400)
            u.status = "disabled"
            db.add(AdminAudit(
                admin_id=admin.id, admin_username=admin.username,
                action="disable_user", target_type="user", target_id=user_id,
                detail=json.dumps({"previous_status": "active"}), ip_address=ip,
            ))
            await db.commit()
            return {"id": u.id, "username": u.username, "status": u.status}

    async def restore_user(self, user_id: int, admin: User, ip: str | None = None) -> dict:
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not u:
                raise BusinessError("USER_NOT_FOUND", "用户不存在", 404)
            u.status = "active"
            db.add(AdminAudit(
                admin_id=admin.id, admin_username=admin.username,
                action="restore_user", target_type="user", target_id=user_id,
                detail=json.dumps({"previous_status": "disabled"}), ip_address=ip,
            ))
            await db.commit()
            return {"id": u.id, "username": u.username, "status": u.status}

    async def record_audit(
        self, admin: User, action: str, target_type: str, target_id: int, ip: str | None = None,
    ) -> None:
        """通用审计记录方法，供各管理员 API 调用。"""
        import json
        async with AsyncSessionLocal() as db:
            db.add(AdminAudit(
                admin_id=admin.id, admin_username=admin.username,
                action=action, target_type=target_type, target_id=target_id,
                detail=json.dumps({}), ip_address=ip,
            ))
            await db.commit()

    # ── 审计日志 ──────────────────────────────────────

    async def list_audits(
        self,
        admin_id: int | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        async with AsyncSessionLocal() as db:
            conditions = []
            if admin_id:
                conditions.append(AdminAudit.admin_id == admin_id)
            if action:
                conditions.append(AdminAudit.action == action)

            base = select(AdminAudit)
            if conditions:
                base = base.where(*conditions)
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await db.execute(count_stmt)).scalar() or 0

            rows = (await db.execute(
                base.order_by(desc(AdminAudit.id)).offset(offset).limit(page_size)
            )).scalars().all()
            items = [{
                "id": a.id, "admin_id": a.admin_id, "admin_username": a.admin_username,
                "action": a.action, "target_type": a.target_type, "target_id": a.target_id,
                "detail": json.loads(a.detail) if a.detail else None,
                "ip_address": a.ip_address,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            } for a in rows]
            pages = (total + page_size - 1) // page_size
            return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": pages}


def _safe_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


admin_service = AdminService()
