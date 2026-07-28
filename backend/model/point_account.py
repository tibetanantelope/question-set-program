from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.model import Base


class PointAccount(Base):
    __tablename__ = "point_account"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_point_account_balance"),
        CheckConstraint("earned_total >= 0", name="ck_point_account_earned_total"),
        CheckConstraint("spent_total >= 0", name="ck_point_account_spent_total"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True)
    balance = Column(Integer, nullable=False, default=0, server_default="0")
    earned_total = Column(Integer, nullable=False, default=0, server_default="0")
    spent_total = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    transactions = relationship("PointTransaction", back_populates="account")
