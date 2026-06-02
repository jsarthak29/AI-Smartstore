from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_tenant_id
from app.database import get_db
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.schemas.product import (
    ForecastResponse,
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductUpdate,
)
from app.services.forecast_service import compute_forecast
from app.ws.manager import broadcast_stock_update

router = APIRouter(prefix="/products", tags=["products"])


def _status_for(p: Product) -> str:
    today = date.today()
    if p.expiry_date and p.expiry_date <= today:
        return "expired"
    if p.stock <= 0:
        return "critical"
    if p.stock < p.reorder_threshold:
        return "low"
    return "ok"


def _serialize(p: Product) -> dict:
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "stock": p.stock,
        "unit_price": float(p.unit_price),
        "expiry_date": p.expiry_date,
        "reorder_threshold": p.reorder_threshold,
        "preferred_supplier_id": p.preferred_supplier_id,
        "is_active": p.is_active,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "stock_status": _status_for(p),
    }


@router.get("", response_model=ProductPage)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    stmt = select(Product).where(Product.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if category:
        stmt = stmt.where(Product.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Product.name).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()

    items = [_serialize(p) for p in rows]
    if status_filter:
        items = [i for i in items if i["stock_status"] == status_filter]
    return ProductPage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    existing = await db.execute(
        select(Product).where(and_(Product.tenant_id == tenant_id, Product.sku == payload.sku))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "sku already exists")
    p = Product(tenant_id=tenant_id, **payload.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    if p.stock:
        db.add(StockMovement(tenant_id=tenant_id, product_id=p.id, delta=p.stock, source="initial"))
        await db.commit()
    return _serialize(p)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    p = (await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    return _serialize(p)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    p = (await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    data = payload.model_dump(exclude_unset=True)
    stock_changed = "stock" in data and data["stock"] != p.stock
    old_stock = p.stock
    for k, v in data.items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    if stock_changed:
        db.add(StockMovement(
            tenant_id=tenant_id,
            product_id=p.id,
            delta=p.stock - old_stock,
            source="adjustment",
        ))
        await db.commit()
        await broadcast_stock_update(tenant_id, p.id, p.stock)
    return _serialize(p)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    p = (await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    p.is_active = False
    await db.commit()


@router.get("/{product_id}/forecast", response_model=ForecastResponse)
async def forecast(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    p = (await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    return await compute_forecast(db, tenant_id, product_id)
