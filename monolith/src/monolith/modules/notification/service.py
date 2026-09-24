"""Public interface of the notification module.

Other modules may import ONLY this file from notification; never its api/, domain/ or infra/.
"""

import uuid
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.customer import service as customer_service
from monolith.modules.notification.domain.model import order_status_email
from monolith.modules.notification.infra.models import NotificationLogRow

__all__ = ["notify_order_status"]

log = structlog.get_logger(__name__)


async def notify_order_status(
    session: AsyncSession,
    order_id: UUID,
    customer_id: UUID,
    status: str,
    reason: str | None = None,
) -> None:
    """'Send' an email: write it to notification_log (same transaction) and to the log."""
    customer = await customer_service.get_customer(session, customer_id)
    if customer is None:  # the order module checked this already; stay safe anyway
        log.warning("notification_skipped_unknown_customer", customer_id=str(customer_id))
        return
    email = order_status_email(customer.cust_nm, customer.cust_eml, order_id, status, reason)
    session.add(
        NotificationLogRow(
            id=uuid.uuid4(),
            order_id=order_id,
            order_status=status,
            recipient=email.to,
            subject=email.subject,
            body=email.body,
        )
    )
    await session.flush()
    log.info("email_sent", order_id=str(order_id), to=email.to, subject=email.subject)
