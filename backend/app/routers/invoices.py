import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_tenant_id
from app.database import get_db
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.schemas.invoice import InvoiceParseResponse, ParsedInvoice, ReceiveRequest
from app.services.ocr_service import parse_invoice
from app.ws.manager import broadcast_stock_update

settings = get_settings()

router = APIRouter(tags=["invoices"])

ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "application/pdf"}


@router.post("/invoices/parse", response_model=InvoiceParseResponse)
async def parse(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unsupported content type {file.content_type}")
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix or {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}[file.content_type]
    dest = upload_dir / f"{uuid.uuid4().hex}{ext}"
    contents = await file.read()
    dest.write_bytes(contents)

    try:
        parsed = parse_invoice(dest)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"OCR failed: {e}")

    # best-effort supplier match by name
    supplier_id = None
    if parsed.get("supplier_name"):
        sup = (await db.execute(
            select(Supplier).where(and_(
                Supplier.tenant_id == tenant_id,
                Supplier.name.ilike(f"%{parsed['supplier_name']}%"),
            ))
        )).scalar_one_or_none()
        if sup:
            supplier_id = sup.id

    # best-effort product match per line item
    for li in parsed.get("line_items", []):
        prod = (await db.execute(
            select(Product).where(and_(
                Product.tenant_id == tenant_id,
                Product.name.ilike(f"%{li.get('name','')}%"),
            )).limit(1)
        )).scalar_one_or_none()
        if prod:
            li["matched_product_id"] = prod.id

    inv = Invoice(tenant_id=tenant_id, supplier_id=supplier_id, raw_path=str(dest), parsed_json=parsed)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return InvoiceParseResponse(invoice_id=inv.id, parsed=ParsedInvoice(**parsed))


@router.post("/inventory/receive", status_code=200)
async def receive(
    payload: ReceiveRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    updated: list[dict] = []
    for line in payload.lines:
        p = (await db.execute(
            select(Product).where(and_(Product.id == line.product_id, Product.tenant_id == tenant_id))
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"product {line.product_id} not in tenant")
        p.stock += line.qty
        p.unit_price = line.unit_price  # latest cost
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=p.id, delta=line.qty, source="invoice"
        ))
        updated.append({"product_id": p.id, "new_stock": p.stock})

    if payload.invoice_id:
        inv = (await db.execute(
            select(Invoice).where(and_(Invoice.id == payload.invoice_id, Invoice.tenant_id == tenant_id))
        )).scalar_one_or_none()
        if inv:
            inv.confirmed = True
            if payload.supplier_id and not inv.supplier_id:
                inv.supplier_id = payload.supplier_id

    await db.commit()
    for u in updated:
        await broadcast_stock_update(tenant_id, u["product_id"], u["new_stock"])
    return {"updated": updated}
