from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from backend.model import Base


class UsageRecord(Base):
    __tablename__ = "usage_record"
    __table_args__ = (
        Index("idx_usage_record_daily_feature", "user_id", "usage_date", "feature"),
        Index("idx_usage_record_source", "usage_source"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    request_id = Column(String(64), nullable=False, unique=True)
    usage_date = Column(Date, nullable=False)
    feature = Column(String(32), nullable=False)
    usage_source = Column(String(16), nullable=False, default="quota", server_default="quota")
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
