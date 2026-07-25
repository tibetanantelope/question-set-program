"""跨模块数据模型：供成员四 Service 查询的关联表。

这些表由成员二（mistake/review_plan）和成员三（knowledge_mastery）负责写入，
成员四只读取，因此使用 raw SQL 查询。
ORM 模型仅用于 create_all 自动建表，确保本地开发和测试环境完整。
"""

from sqlalchemy import (
    Integer, Column, String, DateTime, Date, SmallInteger, ForeignKey, Text,
)
from sqlalchemy.sql import func

from backend.model import Base


class Mistake(Base):
    """错题表（由成员三写入）"""
    __tablename__ = 'mistake'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    knowledge_point_name = Column(String(200), default=None)
    error_type = Column(String(20), default=None, comment='knowledge/calculation/reading/method')
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())


class ReviewPlan(Base):
    """复习计划表（由成员三写入）"""
    __tablename__ = 'review_plan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mistake_id = Column(Integer, ForeignKey('mistake.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    review_date = Column(Date, nullable=False)
    is_completed = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())


class KnowledgeMastery(Base):
    """知识点掌握度表（由成员二写入）"""
    __tablename__ = 'knowledge_mastery'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    knowledge_point_name = Column(String(200), nullable=False)
    mastery_score = Column(Integer, default=0, comment='0-100 掌握度分数')
    last_studied_at = Column(DateTime, default=None)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
