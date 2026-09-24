"""Public interface of the shipping module.

Other modules may import ONLY this file from shipping; never its api/, domain/ or infra/.
"""

import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.shipping.domain.model import Shipment
from monolith.modules.shipping.infra.models import ShipmentRow

__all__ = ["Shipment", "create_shipment"]


async def create_shipment(session: AsyncSession, order_id: UUID) -> Shipment:
    """Simulated courier booking: always succeeds in Phase 0 (failure injection is Phase 3)."""
    shipment = Shipment(id=uuid.uuid4(), order_id=order_id, status="CREATED")
    session.add(ShipmentRow(id=shipment.id, order_id=order_id, status=shipment.status))
    await session.flush()
    return shipment
