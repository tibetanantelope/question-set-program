from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

from backend.model import AsyncSessionLocal
from backend.model.user_profile import UserProfile


class UserProfileMapper:
    def __init__(self, session_factory: AsyncSessionLocal):
        self.session_factory = session_factory

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_by_user_id(self, user_id: int) -> Optional[UserProfile]:
        """根据用户ID获取画像 ORM 对象。未找到返回 None。"""
        async with self.session_factory() as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 创建
    # ------------------------------------------------------------------

    async def create(self, profile: UserProfile) -> UserProfile:
        """创建用户画像。"""
        async with self.session_factory() as session:
            try:
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
                return profile
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ------------------------------------------------------------------
    # 更新
    # ------------------------------------------------------------------

    async def update(self, user_id: int, **fields) -> Optional[UserProfile]:
        """部分更新用户画像，传入需要变更的字段即可。"""
        async with self.session_factory() as session:
            try:
                stmt = select(UserProfile).where(UserProfile.user_id == user_id)
                result = await session.execute(stmt)
                profile = result.scalar_one_or_none()
                if profile is None:
                    return None

                for key, value in fields.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)

                await session.commit()
                await session.refresh(profile)
                return profile
            except SQLAlchemyError:
                await session.rollback()
                raise

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------

    async def delete(self, user_id: int) -> bool:
        """删除用户画像。返回 True 表示删除成功，False 表示不存在。"""
        async with self.session_factory() as session:
            try:
                stmt = select(UserProfile).where(UserProfile.user_id == user_id)
                result = await session.execute(stmt)
                profile = result.scalar_one_or_none()
                if profile is None:
                    return False
                await session.delete(profile)
                await session.commit()
                return True
            except SQLAlchemyError:
                await session.rollback()
                raise


# ---- 依赖注入 ----

async def get_user_profile_mapper() -> UserProfileMapper:
    return UserProfileMapper(AsyncSessionLocal)
