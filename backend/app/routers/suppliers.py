from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_tenant_id, require_admin
from app.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    rows = (await db.execute(
        select(Supplier).where(Supplier.tenant_id == tenant_id).order_by(Supplier.name)
    )).scalars().all()
    return rows


@router.post("", response_model=SupplierOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    s = Supplier(tenant_id=tenant_id, **payload.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    s = (await db.execute(
        select(Supplier).where(and_(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "supplier not found")
    return s


@router.patch("/{supplier_id}", response_model=SupplierOut, dependencies=[Depends(require_admin)])
async def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    s = (await db.execute(
        select(Supplier).where(and_(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "supplier not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/{supplier_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    s = (await db.execute(
        select(Supplier).where(and_(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "supplier not found")
    await db.delete(s)
    await db.commit()
