from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Product:
    id: UUID
    name: str
    price_minor: int
    currency: str
    stock_qty: int


@dataclass(frozen=True, slots=True)
class StockLine:
    """A request to take `quantity` units of one product."""

    product_id: UUID
    quantity: int


class ProductNotFoundError(Exception):
    def __init__(self, product_ids: list[UUID]) -> None:
        super().__init__(f"unknown product(s): {', '.join(map(str, product_ids))}")
        self.product_ids = product_ids


class InsufficientStockError(Exception):
    def __init__(self, product_id: UUID) -> None:
        super().__init__(f"insufficient stock for product {product_id}")
        self.product_id = product_id
