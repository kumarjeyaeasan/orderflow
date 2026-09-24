import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="shipping")


class ShipmentRow(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
