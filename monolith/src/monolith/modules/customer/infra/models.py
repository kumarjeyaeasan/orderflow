import uuid

from sqlalchemy import MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="customer")


class CustomerRow(Base):
    __tablename__ = "customers"

    cust_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    cust_nm: Mapped[str] = mapped_column(Text)
    cust_eml: Mapped[str] = mapped_column(Text)
