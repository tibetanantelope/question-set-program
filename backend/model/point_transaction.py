from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.model import Base


class PointTransaction(Base):
    __tablename__ = "point_transaction"
    __table_args__ = (
        CheckConstraint("change_amount <> 0", name="ck_point_transaction_change"),
        CheckConstraint("balance_after >= 0", name="ck_point_transaction_balance"),
        Index("idx_point_transaction_user_created", "user_id", "created_at"),
        Index("idx_point_transaction_business_type", "business_type"),
        Index(
            "uq_point_transaction_business",
            "user_id",
            "business_type",
            "business_id",
            unique=True,
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(
        BigInteger,
        ForeignKey("point_account.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id = Column(String(64), nullable=False, unique=True)
    business_type = Column(String(32), nullable=False)
    business_id = Column(String(64), nullable=True)
    change_amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    account = relationship("PointAccount", back_populates="transactions")
