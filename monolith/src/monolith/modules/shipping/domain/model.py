from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Shipment:
    id: UUID
    order_id: UUID
    status: str
