from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Payment:
    id: UUID
    order_id: UUID
    customer_id: UUID
    amount_minor: int
    currency: str


class WalletNotFoundError(Exception):
    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"no wallet for customer {customer_id}")
        self.customer_id = customer_id


class InsufficientFundsError(Exception):
    def __init__(self, customer_id: UUID, amount_minor: int) -> None:
        super().__init__(f"customer {customer_id} cannot pay {amount_minor}")
        self.customer_id = customer_id
        self.amount_minor = amount_minor


class CurrencyMismatchError(Exception):
    pass
