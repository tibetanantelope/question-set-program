from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    user_id: int = Field(description='用户ID', json_schema_extra={'example': 1}, gt=0)
    grade: str = Field(description='年级', json_schema_extra={'example': '七年级'})
    subject: str = Field(description='主修学科', json_schema_extra={'example': '数学'})
    weak_points: dict = Field(description='薄弱知识点', json_schema_extra={'example': {'数学': '导数'}})
    preferences: dict = Field(description='长期偏好', json_schema_extra={'example': {'学习方式': '视频'}})
