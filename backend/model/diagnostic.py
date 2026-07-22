from sqlalchemy import Integer, Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from backend.model import Base


class DiagnosticSession(Base):
    __tablename__ = 'diagnostic_session'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, comment='用户ID')
    status = Column(String(32), nullable=False, default='in_progress', comment='in_progress/completed/skipped')
    question_count = Column(Integer, nullable=False, default=5, comment='诊断题目数量')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    completed_at = Column(DateTime, default=None, comment='完成时间')


class DiagnosticAnswer(Base):
    __tablename__ = 'diagnostic_answer'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    diagnostic_id = Column(Integer, nullable=False, comment='诊断会话ID')
    question_id = Column(Integer, nullable=False, comment='题目编号（诊断内自增）')
    content = Column(Text, nullable=False, comment='题目内容')
    question_type = Column(String(32), nullable=False, default='short_answer', comment='题型')
    difficulty = Column(String(32), nullable=False, default='easy', comment='难度: easy/medium/hard')
    knowledge_point_id = Column(Integer, default=None, comment='知识点ID')
    knowledge_point_name = Column(String(128), default=None, comment='知识点名称')
    user_answer = Column(Text, default=None, comment='学生答案')
    is_correct = Column(Boolean, default=None, comment='判题结果')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
