import uuid

from sqlalchemy import CHAR, BigInteger, Integer, MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="inventory")


class ProductRow(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3))
    stock_qty: Mapped[int] = mapped_column(Integer)
