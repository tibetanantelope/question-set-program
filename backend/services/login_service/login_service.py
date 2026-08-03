import json
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.model import get_db
from backend.model.user import User, AdminAudit
from backend.core.security import verify_password, get_password_hash, create_access_token
from backend.core.exceptions import BusinessError


class LoginService:
    async def login(
        self, username: str, password: str, ip_address: str | None = None
    ) -> dict:
        async for db in get_db():
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if not user or not verify_password(password, user.password):
                raise BusinessError("INVALID_CREDENTIALS", "用户名或密码错误", 401)
            if user.status == "disabled":
                raise BusinessError("ACCOUNT_DISABLED", "账号已被禁用，请联系管理员", 403)

            token = create_access_token({
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
            })

            # 管理员登录写入审计
            if user.is_admin:
                db.add(AdminAudit(
                    admin_id=user.id,
                    admin_username=user.username,
                    action="login",
                    ip_address=ip_address,
                ))
                await db.commit()

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                },
            }

    async def register(self, username: str, password: str) -> dict:
        if not username or not password:
            raise BusinessError("INVALID_INPUT", "用户名或密码为空", 400)
        if len(username) < 6 or len(password) < 6:
            raise BusinessError("INVALID_INPUT", "用户名和密码至少需要 6 位", 400)

        async for db in get_db():
            result = await db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                raise BusinessError("USERNAME_EXISTS", "用户名已存在", 400)

            new_user = User(
                username=username,
                password=get_password_hash(password),
                role="user",
                status="active",
            )
            db.add(new_user)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise BusinessError("USERNAME_EXISTS", "用户名已存在", 400)
            await db.refresh(new_user)
            return {
                "id": new_user.id,
                "username": new_user.username,
                "role": new_user.role,
            }

    async def get_my_info(self, user_id: int) -> dict:
        async for db in get_db():
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise BusinessError("USER_NOT_FOUND", "用户不存在", 404)
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
            }


login_service = LoginService()
