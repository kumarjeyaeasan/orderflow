"""Public interface of the customer module.

Other modules may import ONLY this file from customer; never its api/, domain/ or infra/.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.customer.domain.model import Customer
from monolith.modules.customer.infra.models import CustomerRow

__all__ = ["Customer", "get_customer"]


async def get_customer(session: AsyncSession, customer_id: UUID) -> Customer | None:
    row = await session.get(CustomerRow, customer_id)
    if row is None:
        return None
    return Customer(cust_id=row.cust_id, cust_nm=row.cust_nm, cust_eml=row.cust_eml)
