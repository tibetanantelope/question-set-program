"""成员二：智能诊断、练习生成、答题相关数据模型"""

from sqlalchemy import Integer, Column, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func
from backend.model import Base


class LearningSession(Base):
    """学习会话表 - 记录一次完整的学习会话"""
    __tablename__ = 'learning_session'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    session_key = Column(String(128), nullable=True, comment='会话标识（用于关联短期记忆）')
    status = Column(String(32), nullable=False, default='active', comment='active/completed/abandoned')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    completed_at = Column(DateTime, default=None, comment='完成时间')


class Diagnosis(Base):
    """学情诊断表 - 记录用户输入及诊断结果"""
    __tablename__ = 'diagnosis'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    session_id = Column(Integer, nullable=True, comment='关联学习会话ID')
    input_type = Column(String(32), nullable=False, comment='question/learning_question/weakness')
    content = Column(Text, nullable=False, comment='用户输入的题目、问题或薄弱点描述')
    knowledge_point_id = Column(Integer, nullable=True, comment='识别出的知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='识别出的知识点名称')
    mastery_score = Column(Integer, default=60, comment='当前掌握度: 0-100')
    learning_status = Column(String(32), default='consolidating', comment='weak/consolidating/mastered')
    weakness = Column(Text, nullable=True, comment='薄弱点分析')
    practice_suggestion = Column(Text, nullable=True, comment='建议练习方向')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')


class Practice(Base):
    """练习组表 - 记录一组练习（3-5题）"""
    __tablename__ = 'practice'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    diagnosis_id = Column(Integer, nullable=True, comment='关联诊断ID')
    knowledge_point_id = Column(Integer, nullable=True, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='知识点名称')
    difficulty = Column(String(32), nullable=False, default='easy', comment='easy/medium/hard')
    status = Column(String(32), nullable=False, default='in_progress', comment='in_progress/completed')
    question_count = Column(Integer, nullable=False, default=3, comment='题目数量')
    correct_count = Column(Integer, default=0, comment='答对数量')
    accuracy = Column(Float, default=0.0, comment='正确率')
    is_valid = Column(Boolean, default=False, comment='是否为有效练习（成功生成且提交）')
    request_id = Column(String(128), nullable=True, unique=True, comment='幂等标识')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    submitted_at = Column(DateTime, default=None, comment='提交时间')


class Question(Base):
    """题目表 - 记录生成的每道题目"""
    __tablename__ = 'question'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    practice_id = Column(Integer, nullable=False, index=True, comment='关联练习组ID')
    question_order = Column(Integer, nullable=False, comment='题目序号（组内）')
    content = Column(Text, nullable=False, comment='题目内容')
    question_type = Column(String(32), nullable=False, default='short_answer', comment='题型')
    difficulty = Column(String(32), nullable=False, default='easy', comment='easy/medium/hard')
    knowledge_point_id = Column(Integer, nullable=True, comment='知识点ID')
    knowledge_point_name = Column(String(128), nullable=True, comment='知识点名称')
    standard_answer = Column(Text, nullable=True, comment='标准答案')
    analysis = Column(Text, nullable=True, comment='基础解析')
    user_answer = Column(Text, nullable=True, comment='学生答案')
    is_correct = Column(Boolean, default=None, comment='判断结果')
    error_type = Column(String(32), nullable=True, comment='knowledge/calculation/reading/method')
    error_description = Column(Text, nullable=True, comment='错因说明')
    next_suggestion = Column(Text, nullable=True, comment='下一步建议')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    answered_at = Column(DateTime, default=None, comment='答题时间')
