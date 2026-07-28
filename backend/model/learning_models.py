"""成员四数据模型：学习记录、每日计划、站内提醒、学情报告"""

from sqlalchemy import (
    Integer, Column, String, DateTime, Date, JSON, DECIMAL, SmallInteger, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from backend.model import Base


class LearningRecord(Base):
    __tablename__ = 'learning_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    record_type = Column(String(20), nullable=False, comment='diagnosis/practice/correction/review/report')
    title = Column(String(200), nullable=False)
    subject = Column(String(32), default=None)
    knowledge_point_name = Column(String(200), default=None)
    question_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    accuracy = Column(DECIMAL(5, 2), default=None)
    mastery_change = Column(Integer, default=0)
    request_id = Column(String(64), default=None, unique=True)
    occurred_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())


class DailyPlan(Base):
    __tablename__ = 'daily_plan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    plan_date = Column(Date, nullable=False)
    target_groups = Column(Integer, nullable=False, default=3)
    completed_groups = Column(Integer, nullable=False, default=0)
    is_completed = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())


class Notification(Base):
    __tablename__ = 'notification'
    __table_args__ = (
        UniqueConstraint('user_id', 'dedupe_key', name='uq_notification_user_dedupe'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    type = Column(String(20), nullable=False, comment='review_due/daily_plan/vip_expiring')
    title = Column(String(200), nullable=False)
    content = Column(String(500), default=None)
    dedupe_key = Column(String(100), default=None, comment='同一用户的提醒幂等键')
    is_read = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())


class LearningReport(Base):
    __tablename__ = 'learning_report'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    practice_count = Column(Integer, nullable=False, default=0)
    question_count = Column(Integer, nullable=False, default=0)
    accuracy = Column(DECIMAL(5, 2), default=None)
    mastery_change = Column(Integer, default=0)
    frequent_error_type = Column(String(20), default=None, comment='knowledge/calculation/reading/method')
    weak_points = Column(JSON, default=None)
    suggestion = Column(String(500), default=None)
    request_id = Column(String(64), default=None, unique=True)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
