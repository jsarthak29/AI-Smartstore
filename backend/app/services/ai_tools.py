"""Tool registry for the AI Store Assistant.

Each tool is a pair of (Gemini function-declaration schema, tenant-scoped python implementation).
All implementations run against the real database and are filtered by tenant_id — the LLM cannot
see or mutate cross-tenant data.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase_order import POLine, POStatus, PurchaseOrder
from app.models.supplier import Supplier

# ---------- function declarations (Gemini schema) ----------

TOOL_SCHEMAS = [
    {
        "name": "get_low_stock_products",
        "description": "List products at or below their reorder threshold. Use when the user asks about reordering, running out, or stock alerts.",
        "parameters": {
            "type": "object",
            "properties": {
                "threshold_pct": {
                    "type": "number",
                    "description": "Treat as low when stock < reorder_threshold * (1 + threshold_pct/100). Default 0 means strict threshold.",
                }
            },
        },
    },
    {
        "name": "get_product_detail",
        "description": "Return full information about a single product. Use whenever the user asks about a specific item.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product DB id (preferred)."},
                "product_name": {"type": "string", "description": "Case-insensitive partial name; first match wins."},
            },
        },
    },
    {
        "name": "get_po_history",
        "description": "List recent purchase orders, optionally filtered by supplier or recency.",
        "parameters": {
            "type": "object",
            "properties": {
                "supplier_name": {"type": "string"},
                "days": {"type": "integer", "description": "Look-back window. Default 30."},
            },
        },
    },
    {
        "name": "get_expiring_products",
        "description": "List products that will expire within N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "Default 14."}
            },
        },
    },
    {
        "name": "create_draft_po",
        "description": "Create a new Draft purchase order for a supplier with the given line items. Use when the user asks to draft, place, or generate a PO.",
        "parameters": {
            "type": "object",
            "required": ["supplier_id", "line_items"],
            "properties": {
                "supplier_id": {"type": "integer"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["product_id", "qty"],
                        "properties": {
                            "product_id": {"type": "integer"},
                            "qty": {"type": "integer"},
                        },
                    },
                },
                "notes": {"type": "string"},
            },
        },
    },
]


# ---------- implementations ----------

async def get_low_stock_products(db: AsyncSession, tenant_id: int, threshold_pct: float = 0) -> dict:
    factor = 1 + (threshold_pct or 0) / 100
    rows = (await db.execute(
        select(Product).where(and_(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
        ))
    )).scalars().all()
    out = []
    for p in rows:
        if p.stock < p.reorder_threshold * factor:
            out.append({
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "stock": p.stock,
                "reorder_threshold": p.reorder_threshold,
                "suggested_reorder_qty": max(p.reorder_threshold * 2 - p.stock, 1),
                "preferred_supplier_id": p.preferred_supplier_id,
            })
    return {"count": len(out), "products": out}


async def get_product_detail(db: AsyncSession, tenant_id: int, product_id: int | None = None, product_name: str | None = None) -> dict:
    if not product_id and not product_name:
        return {"error": "provide product_id or product_name"}
    stmt = select(Product).where(Product.tenant_id == tenant_id)
    if product_id:
        stmt = stmt.where(Product.id == product_id)
    else:
        stmt = stmt.where(Product.name.ilike(f"%{product_name}%"))
    p = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if not p:
        return {"error": "product not found"}
    supplier_name = None
    if p.preferred_supplier_id:
        s = (await db.execute(select(Supplier).where(Supplier.id == p.preferred_supplier_id))).scalar_one_or_none()
        supplier_name = s.name if s else None
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "stock": p.stock,
        "unit_price": float(p.unit_price),
        "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
        "reorder_threshold": p.reorder_threshold,
        "preferred_supplier_id": p.preferred_supplier_id,
        "preferred_supplier_name": supplier_name,
    }


async def get_po_history(db: AsyncSession, tenant_id: int, supplier_name: str | None = None, days: int = 30) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days or 30)
    stmt = select(PurchaseOrder).where(and_(
        PurchaseOrder.tenant_id == tenant_id,
        PurchaseOrder.created_at >= cutoff,
    ))
    if supplier_name:
        sup = (await db.execute(
            select(Supplier).where(and_(Supplier.tenant_id == tenant_id, Supplier.name.ilike(f"%{supplier_name}%")))
        )).scalar_one_or_none()
        if not sup:
            return {"count": 0, "purchase_orders": []}
        stmt = stmt.where(PurchaseOrder.supplier_id == sup.id)
    rows = (await db.execute(stmt.order_by(PurchaseOrder.created_at.desc()))).scalars().all()
    out = []
    for po in rows:
        out.append({
            "id": po.id,
            "supplier_id": po.supplier_id,
            "status": po.status,
            "total": float(po.total or 0),
            "created_at": po.created_at.isoformat(),
            "line_count": len(po.lines),
        })
    return {"count": len(out), "purchase_orders": out}


async def get_expiring_products(db: AsyncSession, tenant_id: int, days_ahead: int = 14) -> dict:
    cutoff = date.today() + timedelta(days=days_ahead or 14)
    rows = (await db.execute(
        select(Product).where(and_(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.expiry_date.is_not(None),
            Product.expiry_date <= cutoff,
        ))
    )).scalars().all()
    out = [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "stock": p.stock,
            "expiry_date": p.expiry_date.isoformat(),
            "days_to_expiry": (p.expiry_date - date.today()).days,
        }
        for p in rows
    ]
    return {"count": len(out), "products": out}


async def create_draft_po(db: AsyncSession, tenant_id: int, user_id: int,
                          supplier_id: int, line_items: list[dict], notes: str | None = None) -> dict:
    sup = (await db.execute(
        select(Supplier).where(and_(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id))
    )).scalar_one_or_none()
    if not sup:
        return {"error": "supplier not found in tenant"}

    pids = [li["product_id"] for li in line_items]
    products = {
        p.id: p for p in (await db.execute(
            select(Product).where(and_(Product.id.in_(pids), Product.tenant_id == tenant_id))
        )).scalars().all()
    }
    if len(products) != len(set(pids)):
        return {"error": "one or more products not in tenant"}

    po = PurchaseOrder(
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        status=POStatus.DRAFT.value,
        notes=notes or "Created by AI assistant",
        created_by=user_id,
        total=0,
    )
    db.add(po)
    await db.flush()
    total = 0.0
    for item in line_items:
        prod = products[item["product_id"]]
        unit_price = float(prod.unit_price)
        db.add(POLine(po_id=po.id, product_id=prod.id, qty=int(item["qty"]), unit_price=unit_price))
        total += unit_price * int(item["qty"])
    po.total = total
    await db.commit()
    await db.refresh(po)
    return {
        "po_id": po.id,
        "status": po.status,
        "total": float(po.total),
        "line_count": len(line_items),
    }


# ---------- dispatcher ----------

async def dispatch_tool(name: str, args: dict, db: AsyncSession, tenant_id: int, user_id: int) -> dict:
    if name == "get_low_stock_products":
        return await get_low_stock_products(db, tenant_id, args.get("threshold_pct", 0))
    if name == "get_product_detail":
        return await get_product_detail(db, tenant_id, args.get("product_id"), args.get("product_name"))
    if name == "get_po_history":
        return await get_po_history(db, tenant_id, args.get("supplier_name"), args.get("days", 30))
    if name == "get_expiring_products":
        return await get_expiring_products(db, tenant_id, args.get("days_ahead", 14))
    if name == "create_draft_po":
        return await create_draft_po(
            db, tenant_id, user_id,
            supplier_id=int(args["supplier_id"]),
            line_items=args["line_items"],
            notes=args.get("notes"),
        )
    return {"error": f"unknown tool {name}"}
