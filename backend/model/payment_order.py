from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.sql import func

from backend.model import Base


class PaymentOrder(Base):
    __tablename__ = "payment_order"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_order_amount"),
        Index("idx_payment_order_user_created", "user_id", "created_at"),
        Index("idx_payment_order_status", "status"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_no = Column(String(32), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    request_id = Column(String(64), nullable=False, unique=True)
    plan = Column(String(32), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    alipay_trade_no = Column(String(64), nullable=True, unique=True)
    paid_at = Column(DateTime, nullable=True)
    vip_applied_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
