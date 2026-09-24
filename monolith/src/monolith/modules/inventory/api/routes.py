from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from monolith.db import SessionMaker
from monolith.modules.inventory import service

router = APIRouter(tags=["inventory"])


class ProductOut(BaseModel):
    id: UUID
    name: str
    price_minor: int
    currency: str
    stock_qty: int


class StockAdjustIn(BaseModel):
    delta: int  # negative to remove stock


class StockOut(BaseModel):
    product_id: UUID
    stock_qty: int


@router.get("/products")
async def list_products(sm: SessionMaker) -> list[ProductOut]:
    async with sm() as session:
        products = await service.list_products(session)
    return [ProductOut.model_validate(p, from_attributes=True) for p in products]


@router.get("/products/{product_id}")
async def get_product(product_id: UUID, sm: SessionMaker) -> ProductOut:
    async with sm() as session:
        product = await service.get_product(session, product_id)
    if product is None:
        raise HTTPException(404, f"unknown product {product_id}")
    return ProductOut.model_validate(product, from_attributes=True)


@router.post("/admin/products/{product_id}/stock")
async def adjust_stock(product_id: UUID, body: StockAdjustIn, sm: SessionMaker) -> StockOut:
    try:
        async with sm() as session, session.begin():
            qty = await service.adjust_stock(session, product_id, body.delta)
    except service.ProductNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except service.InsufficientStockError as exc:
        raise HTTPException(422, "stock would go negative") from exc
    return StockOut(product_id=product_id, stock_qty=qty)
