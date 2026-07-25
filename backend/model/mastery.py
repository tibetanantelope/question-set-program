"""成员三：答案分析、掌握度、错题订正与复习相关数据模型"""

from sqlalchemy import Integer, Column, String, DateTime, Text, Boolean, Date
from sqlalchemy.sql import func
from backend.model import Base


class AnswerRecord(Base):
    """答题记录表 - 记录每道题的判题结果"""
    __tablename__ = 'answer_record'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    practice_id = Column(Integer, nullable=False, comment='关联练习组ID')
    question_id = Column(Integer, nullable=False, comment='关联题目ID')
    knowledge_point_id = Column(Integer, nullable=True, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='知识点名称')
    difficulty = Column(String(32), nullable=False, default='easy', comment='easy/medium/hard')
    user_answer = Column(Text, nullable=True, comment='学生答案')
    is_correct = Column(Boolean, nullable=False, comment='判断结果')
    error_type = Column(String(32), nullable=True, comment='knowledge/calculation/reading/method')
    error_description = Column(Text, nullable=True, comment='错因说明')
    request_id = Column(String(128), nullable=True, unique=True, comment='幂等标识')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='答题时间')


class KnowledgeMastery(Base):
    """知识点掌握度表 - 每个用户每个知识点一条记录"""
    __tablename__ = 'knowledge_mastery'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    knowledge_point_id = Column(Integer, nullable=False, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=False, comment='知识点名称')
    mastery_score = Column(Integer, nullable=False, default=60, comment='掌握度: 0-100')
    learning_status = Column(String(32), nullable=False, default='consolidating', comment='weak/consolidating/mastered')
    answer_count = Column(Integer, nullable=False, default=0, comment='累计答题次数')
    correct_count = Column(Integer, nullable=False, default=0, comment='累计答对次数')
    last_studied_at = Column(DateTime, default=None, comment='最近一次学习时间')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')


class Mistake(Base):
    """错题记录表"""
    __tablename__ = 'mistake'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    question_id = Column(Integer, nullable=True, comment='关联题目ID')
    question_content = Column(Text, nullable=True, comment='题目内容（冗余）')
    user_answer = Column(Text, nullable=True, comment='学生错误答案')
    standard_answer = Column(Text, nullable=True, comment='标准答案')
    knowledge_point_id = Column(Integer, nullable=True, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='知识点名称')
    difficulty = Column(String(32), nullable=False, default='easy', comment='题目难度')
    error_type = Column(String(32), nullable=True, comment='knowledge/calculation/reading/method')
    correction_status = Column(String(32), nullable=False, default='pending', comment='pending/corrected/review_due')
    correction_answer = Column(Text, nullable=True, comment='订正答案')
    correction_correct = Column(Boolean, default=None, comment='订正是否正确')
    first_correction_success = Column(Boolean, default=False, comment='首次订正成功（积分已发放）')
    correction_request_id = Column(String(128), nullable=True, unique=True, comment='订正幂等标识')
    corrected_at = Column(DateTime, default=None, comment='订正完成时间')
    next_review_at = Column(DateTime, default=None, comment='下一次复习到期时间')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='错题生成时间')
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), comment='更新时间')


class ReviewPlan(Base):
    """复习计划表 - 订正成功后自动生成 1/3/7 天复习记录"""
    __tablename__ = 'review_plan'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, comment='用户ID')
    mistake_id = Column(Integer, nullable=False, comment='关联错题ID')
    knowledge_point_id = Column(Integer, nullable=True, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='知识点名称')
    review_date = Column(Date, nullable=False, comment='复习日期')
    status = Column(String(32), nullable=False, default='pending', comment='pending/completed')
    reviewed_at = Column(DateTime, default=None, comment='实际复习时间')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
