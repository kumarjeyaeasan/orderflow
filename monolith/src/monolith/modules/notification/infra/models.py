import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="notification")


class NotificationLogRow(Base):
    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    order_id: Mapped[uuid.UUID]
    order_status: Mapped[str] = mapped_column(Text)
    recipient: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
