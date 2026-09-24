from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from monolith.db import SessionMaker
from monolith.modules.payment import service

router = APIRouter(tags=["payment"])


class TopUpIn(BaseModel):
    amount_minor: int = Field(gt=0)


class WalletOut(BaseModel):
    customer_id: UUID
    balance_minor: int


@router.post("/admin/customers/{customer_id}/wallet")
async def top_up(customer_id: UUID, body: TopUpIn, sm: SessionMaker) -> WalletOut:
    try:
        async with sm() as session, session.begin():
            balance = await service.top_up(session, customer_id, body.amount_minor)
    except service.WalletNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return WalletOut(customer_id=customer_id, balance_minor=balance)
