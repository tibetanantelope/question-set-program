"""成员一：学生画像 Service —— 基础画像的查询、保存。"""

from typing import Optional

from backend.core.exceptions import BusinessError
from backend.dao.user_profile_mapper import UserProfileMapper, get_user_profile_mapper
from backend.model.user_profile import UserProfile
from backend.schemas.request.user_profile_update_request import UserProfileUpdateRequest
from backend.schemas.response.user_profile_response import StudentProfileSummary, UserProfileResponse

# 画像完善必需字段
_REQUIRED_FIELDS = {'stage', 'grade', 'subject', 'learning_goal'}


class ProfileService:
    def __init__(self, mapper: Optional[UserProfileMapper] = None):
        self._mapper = mapper

    @property
    def mapper(self) -> UserProfileMapper:
        if self._mapper is None:
            self._mapper = UserProfileMapper(
                __import__('backend.model', fromlist=['AsyncSessionLocal']).AsyncSessionLocal
            )
        return self._mapper

    # ------------------------------------------------------------------
    # 画像查询
    # ------------------------------------------------------------------

    async def get_summary(self, user_id: int) -> StudentProfileSummary:
        """供其他 Service 查询当前用户画像摘要。画像不存在或未完善时抛出 BusinessError。"""
        p = await self.mapper.get_by_user_id(user_id)
        if p is None:
            raise BusinessError('PROFILE_NOT_COMPLETED', '请先完善学习信息', 400)
        if not self._is_profile_complete(p):
            raise BusinessError('PROFILE_NOT_COMPLETED', '请先完善学习信息', 400)
        return self._to_summary(p)

    async def get_profile(self, user_id: int) -> UserProfileResponse:
        """查询当前用户画像用于 API 返回。"""
        p = await self.mapper.get_by_user_id(user_id)
        if p is None:
            return UserProfileResponse(profile=None)
        summary = self._to_summary(p) if self._is_profile_complete(p) else None
        return UserProfileResponse(
            profile=summary,
            created_at=p.create_time.isoformat() if p.create_time else None,
            updated_at=p.update_time.isoformat() if p.update_time else None,
        )

    # ------------------------------------------------------------------
    # 画像保存
    # ------------------------------------------------------------------

    async def save_profile(self, user_id: int, req: UserProfileUpdateRequest) -> StudentProfileSummary:
        """创建或更新当前用户画像，返回画像摘要。

        当学段、年级或学科发生变化时，重置诊断状态为 required，
        要求用户重新完成首次诊断。
        """
        p = await self.mapper.get_by_user_id(user_id)
        update_data = req.model_dump(exclude_none=True)

        # 检测学段/年级/学科是否变化，变化则重置诊断
        _identity_fields = {'stage', 'grade', 'subject'}
        if p is not None and any(
            update_data.get(f) and update_data[f] != getattr(p, f, None)
            for f in _identity_fields
        ):
            update_data['diagnostic_status'] = 'required'

        if p is None:
            p = UserProfile(user_id=user_id, **update_data)
            p = await self.mapper.create(p)
        else:
            p = await self.mapper.update(user_id, **update_data)

        return self._to_summary(p)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _is_profile_complete(p: UserProfile) -> bool:
        return bool(p.stage and p.grade and p.subject and p.learning_goal)

    @staticmethod
    def _to_summary(p: UserProfile) -> StudentProfileSummary:
        return StudentProfileSummary(
            stage=p.stage,
            grade=p.grade,
            subject=p.subject,
            learning_goal=p.learning_goal,
            weekly_study_days=p.weekly_study_days,
            daily_target_groups=p.daily_target_groups,
            diagnostic_status=p.diagnostic_status,
        )


# 单例
_profile_service: Optional[ProfileService] = None


async def get_profile_service() -> ProfileService:
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService()
    return _profile_service
