from sqlalchemy import Integer, Column, String, DateTime, Boolean
from sqlalchemy.sql import func

from backend.model import Base


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(20), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(16), nullable=False, default='user', comment='角色: user/admin')
    status = Column(String(16), nullable=False, default='active', comment='状态: active/disabled')

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def is_active(self) -> bool:
        return self.status == 'active'


class AdminAudit(Base):
    __tablename__ = 'admin_audit'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, nullable=False, comment='操作管理员ID')
    admin_username = Column(String(20), nullable=False, comment='操作管理员用户名')
    action = Column(String(64), nullable=False, comment='操作类型')
    target_type = Column(String(32), default=None, comment='操作对象类型')
    target_id = Column(Integer, default=None, comment='操作对象ID')
    detail = Column(String(1024), default=None, comment='操作详情JSON')
    ip_address = Column(String(64), default=None, comment='操作IP')
    created_at = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
