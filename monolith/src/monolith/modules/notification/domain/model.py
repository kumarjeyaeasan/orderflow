from dataclasses import dataclass
from uuid import UUID

_SUBJECTS = {
    "APPROVED": "Your order is confirmed",
    "REJECTED": "We couldn't take your order",
    "SHIPPED": "Your order is on its way",
    "CANCELLED": "Your order was cancelled",
}


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    body: str


def order_status_email(
    name: str, email: str, order_id: UUID, status: str, reason: str | None
) -> Email:
    body = f"Hi {name}, order {order_id} is now {status}."
    if reason:
        body += f" Reason: {reason}."
    return Email(to=email, subject=_SUBJECTS.get(status, f"Order {status}"), body=body)
