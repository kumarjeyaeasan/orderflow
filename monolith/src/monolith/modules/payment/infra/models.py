import uuid
from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, MetaData, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="payment")


class WalletRow(Base):
    __tablename__ = "wallets"

    customer_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    balance_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3))


class PaymentRow(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    customer_id: Mapped[uuid.UUID]
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3))
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
