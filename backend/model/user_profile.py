from sqlalchemy import Integer, Column, String, DateTime, JSON
from sqlalchemy.sql import func
from backend.model import Base


class UserProfile(Base):
    __tablename__ = 'user_profile'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, unique=True, nullable=False, comment='用户唯一ID（业务主键）')
    grade = Column(String(32), nullable=False, comment='年级')
    subject = Column(String(32), nullable=False, default='数学', comment='主修学科')

    # 成员一新增字段
    stage = Column(String(32), nullable=False, default='', comment='学段: primary/junior/senior/university')
    learning_goal = Column(String(32), nullable=False, default='', comment='学习目标: daily/weakness/exam')
    weekly_study_days = Column(Integer, nullable=False, default=5, comment='每周学习天数: 1-7')
    daily_target_groups = Column(Integer, nullable=False, default=3, comment='每日目标练习组数: 1-5')
    diagnostic_status = Column(String(32), nullable=False, default='required', comment='诊断状态: required/in_progress/completed/skipped')

    # 保留旧字段兼容
    weak_points = Column(JSON, nullable=False, default=dict, comment='薄弱知识点（JSON）- 兼容旧字段')
    preferences = Column(JSON, nullable=False, default=dict, comment='长期偏好（JSON）- 兼容旧字段')

    update_time = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')
    create_time = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
