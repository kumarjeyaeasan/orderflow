"""Public interface of the payment module.

Other modules may import ONLY this file from payment; never its api/, domain/ or infra/.
All functions run inside the caller's session/transaction and never commit.
"""

import uuid
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.payment.domain.model import (
    CurrencyMismatchError,
    InsufficientFundsError,
    Payment,
    WalletNotFoundError,
)
from monolith.modules.payment.infra.models import PaymentRow, WalletRow

__all__ = [
    "CurrencyMismatchError",
    "InsufficientFundsError",
    "Payment",
    "WalletNotFoundError",
    "charge",
    "get_balance",
    "top_up",
]


async def _require_wallet(session: AsyncSession, customer_id: UUID, currency: str) -> WalletRow:
    wallet = await session.get(WalletRow, customer_id)
    if wallet is None:
        raise WalletNotFoundError(customer_id)
    if wallet.currency != currency:
        raise CurrencyMismatchError(f"wallet is {wallet.currency}, amount is {currency}")
    return wallet


async def charge(
    session: AsyncSession, order_id: UUID, customer_id: UUID, amount_minor: int, currency: str
) -> Payment:
    """Authorise and capture in one step (a lab simplification; see PROJECT_BRIEF section 2).

    The balance check and the debit are one conditional UPDATE, so two concurrent charges
    can't both spend the same money.
    """
    await _require_wallet(session, customer_id, currency)
    debited = await session.scalar(
        update(WalletRow)
        .where(WalletRow.customer_id == customer_id, WalletRow.balance_minor >= amount_minor)
        .values(balance_minor=WalletRow.balance_minor - amount_minor)
        .returning(WalletRow.customer_id)
    )
    if debited is None:
        raise InsufficientFundsError(customer_id, amount_minor)
    payment = Payment(
        id=uuid.uuid4(),
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=amount_minor,
        currency=currency,
    )
    session.add(
        PaymentRow(
            id=payment.id,
            order_id=order_id,
            customer_id=customer_id,
            amount_minor=amount_minor,
            currency=currency,
            status="CHARGED",
        )
    )
    await session.flush()
    return payment


async def top_up(session: AsyncSession, customer_id: UUID, amount_minor: int) -> int:
    """Admin/demo wallet top-up. Returns the new balance."""
    new_balance = await session.scalar(
        update(WalletRow)
        .where(WalletRow.customer_id == customer_id)
        .values(balance_minor=WalletRow.balance_minor + amount_minor)
        .returning(WalletRow.balance_minor)
    )
    if new_balance is None:
        raise WalletNotFoundError(customer_id)
    return new_balance


async def get_balance(session: AsyncSession, customer_id: UUID) -> int:
    wallet = await session.get(WalletRow, customer_id, populate_existing=True)
    if wallet is None:
        raise WalletNotFoundError(customer_id)
    return wallet.balance_minor
