from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.model import get_db
from backend.model.user import User
from backend.core.security import verify_password, get_password_hash, create_access_token


class LoginService:
    async def login(self, username: str, password: str) -> dict:
        async for db in get_db():
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if user and verify_password(password, user.password):
                token = create_access_token({"user_id": user.id, "username": user.username})
                return {
                    "access_token": token,
                    "token_type": "bearer",
                }
            return {"code": 401, "msg": "用户未注册或密码错误", "data": None}

    async def register(self, username: str, password: str) -> dict:
        if not username or not password:
            return {"code": 400, "msg": "用户名或密码为空", "data": None}

        async for db in get_db():
            result = await db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                return {"code": 400, "msg": "用户名已存在", "data": None}

            new_user = User(username=username, password=get_password_hash(password))
            db.add(new_user)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return {"code": 400, "msg": "用户名已存在", "data": None}
            await db.refresh(new_user)
            return {
                "code": 200,
                "msg": "success",
                "data": {
                    "id": new_user.id,
                    "username": new_user.username,
                },
            }


# 保留旧名称，避免其他尚未迁移的模块导入失败。
loginService = LoginService
