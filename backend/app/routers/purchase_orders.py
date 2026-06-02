from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_tenant_id, require_admin
from app.database import get_db
from app.models.product import Product
from app.models.purchase_order import POLine, POStatus, PurchaseOrder
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.po import POCreate, POOut, POStatusUpdate

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

_ALLOWED_TRANSITIONS = {
    POStatus.DRAFT.value: {POStatus.SENT.value},
    POStatus.SENT.value: {POStatus.ACKNOWLEDGED.value},
    POStatus.ACKNOWLEDGED.value: {POStatus.RECEIVED.value},
    POStatus.RECEIVED.value: set(),
}


def _serialize(po: PurchaseOrder) -> dict:
    return {
        "id": po.id,
        "supplier_id": po.supplier_id,
        "status": po.status,
        "total": float(po.total or 0),
        "notes": po.notes,
        "created_by": po.created_by,
        "created_at": po.created_at,
        "sent_at": po.sent_at,
        "lines": [
            {"id": ln.id, "product_id": ln.product_id, "qty": ln.qty, "unit_price": float(ln.unit_price)}
            for ln in po.lines
        ],
    }


@router.get("", response_model=list[POOut])
async def list_pos(
    supplier_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    days: int | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    stmt = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(PurchaseOrder.created_at >= cutoff)
    rows = (await db.execute(stmt.order_by(PurchaseOrder.created_at.desc()))).scalars().all()
    return [_serialize(po) for po in rows]


@router.post("", response_model=POOut, status_code=201)
async def create_po(
    payload: POCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    supplier = (await db.execute(
        select(Supplier).where(and_(Supplier.id == payload.supplier_id, Supplier.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not supplier:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "supplier not found in tenant")

    product_ids = [ln.product_id for ln in payload.lines]
    products = {
        p.id: p for p in (await db.execute(
            select(Product).where(and_(Product.id.in_(product_ids), Product.tenant_id == tenant_id))
        )).scalars().all()
    }
    if len(products) != len(set(product_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "one or more products not in tenant")

    po = PurchaseOrder(
        tenant_id=tenant_id,
        supplier_id=payload.supplier_id,
        status=POStatus.DRAFT.value,
        notes=payload.notes,
        created_by=user.id,
        total=0,
    )
    db.add(po)
    await db.flush()
    total = 0.0
    for line in payload.lines:
        prod = products[line.product_id]
        unit_price = line.unit_price if line.unit_price is not None else float(prod.unit_price)
        db.add(POLine(po_id=po.id, product_id=line.product_id, qty=line.qty, unit_price=unit_price))
        total += unit_price * line.qty
    po.total = total
    await db.commit()
    await db.refresh(po)
    return _serialize(po)


@router.patch("/{po_id}/status", response_model=POOut)
async def update_status(
    po_id: int,
    payload: POStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    po = (await db.execute(
        select(PurchaseOrder).where(and_(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not po:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "po not found")
    allowed = _ALLOWED_TRANSITIONS.get(po.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"cannot transition from {po.status} to {payload.status}",
        )
    po.status = payload.status
    if payload.status == POStatus.SENT.value:
        po.sent_at = datetime.now(timezone.utc)
    if payload.status == POStatus.RECEIVED.value:
        # apply stock increments
        from app.models.stock_movement import StockMovement
        for line in po.lines:
            prod = (await db.execute(
                select(Product).where(Product.id == line.product_id)
            )).scalar_one_or_none()
            if prod:
                prod.stock += line.qty
                db.add(StockMovement(
                    tenant_id=tenant_id, product_id=prod.id, delta=line.qty, source="receive"
                ))
    await db.commit()
    await db.refresh(po)
    return _serialize(po)


@router.post("/{po_id}/send-email", dependencies=[Depends(require_admin)])
async def send_email(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    po = (await db.execute(
        select(PurchaseOrder).where(and_(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not po:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "po not found")
    supplier = (await db.execute(select(Supplier).where(Supplier.id == po.supplier_id))).scalar_one_or_none()
    # Mock SMTP — log to console
    body = f"PO #{po.id} — {len(po.lines)} line items, total {po.total}"
    print(f"[MOCK EMAIL] to {supplier.email if supplier else '?'}: {body}", flush=True)
    if po.status == POStatus.DRAFT.value:
        po.status = POStatus.SENT.value
        po.sent_at = datetime.now(timezone.utc)
        await db.commit()
    return {"sent_to": supplier.email if supplier else None, "body": body}
