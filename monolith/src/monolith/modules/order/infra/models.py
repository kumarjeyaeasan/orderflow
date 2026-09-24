import uuid
from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, ForeignKey, Integer, MetaData, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(schema="orders")


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[uuid.UUID]
    status: Mapped[str] = mapped_column(Text)
    total_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lines: Mapped[list["OrderLineRow"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderLineRow.product_id"
    )


class OrderLineRow(Base):
    __tablename__ = "order_lines"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.orders.id"), primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger)
