from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.sql import func

from backend.model import Base


class VipInfo(Base):
    __tablename__ = "vip_info"
    __table_args__ = (
        CheckConstraint(
            "started_at IS NULL OR expires_at IS NULL OR expires_at > started_at",
            name="ck_vip_info_period",
        ),
        Index("idx_vip_info_expires_at", "expires_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True)
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
