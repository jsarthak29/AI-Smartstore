import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_log import AutomationLog
from app.models.product import Product
from app.models.purchase_order import POStatus, PurchaseOrder
from app.models.report import Report
from app.models.stock_movement import StockMovement
from app.models.tenant import Tenant

log = logging.getLogger(__name__)

JOB_NAME = "weekly_summary_agent"


async def run(db: AsyncSession) -> None:
    tenants = (await db.execute(select(Tenant))).scalars().all()
    for t in tenants:
        try:
            await _run_for_tenant(db, t.id)
        except Exception as e:
            log.exception("weekly_summary_agent failed for tenant %s", t.id)
            db.add(AutomationLog(tenant_id=t.id, job_name=JOB_NAME, status="error", outcome={"error": str(e)}))
            await db.commit()


async def _run_for_tenant(db: AsyncSession, tenant_id: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    total_products = (await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    )).scalar_one()

    low_stock = (await db.execute(
        select(func.count(Product.id)).where(and_(
            Product.tenant_id == tenant_id, Product.is_active.is_(True),
            Product.stock < Product.reorder_threshold,
        ))
    )).scalar_one()

    # Top 5 movers — by absolute outflow over the last 7 days
    movers_q = (
        select(StockMovement.product_id, func.sum(func.abs(StockMovement.delta)).label("vol"))
        .where(and_(
            StockMovement.tenant_id == tenant_id,
            StockMovement.ts >= cutoff,
            StockMovement.delta < 0,
        ))
        .group_by(StockMovement.product_id)
        .order_by(func.sum(func.abs(StockMovement.delta)).desc())
        .limit(5)
    )
    movers = (await db.execute(movers_q)).all()
    top_lines = []
    sales_value = 0.0
    for pid, vol in movers:
        p = (await db.execute(select(Product).where(Product.id == pid))).scalar_one_or_none()
        if p:
            value = vol * float(p.unit_price)
            sales_value += value
            top_lines.append(f"- **{p.name}** ({p.sku}) — {vol} units, ₹{value:,.2f}")

    pending_pos = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(and_(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status.in_([POStatus.DRAFT.value, POStatus.SENT.value, POStatus.ACKNOWLEDGED.value]),
        ))
    )).scalar_one()

    md = (
        f"# Weekly Summary — {datetime.now(timezone.utc).date().isoformat()}\n\n"
        f"- Total active products: **{total_products}**\n"
        f"- Low-stock alerts: **{low_stock}**\n"
        f"- Pending purchase orders: **{pending_pos}**\n"
        f"- Estimated sales value (last 7d): **₹{sales_value:,.2f}**\n\n"
        f"## Top 5 Movers (last 7 days)\n"
        + ("\n".join(top_lines) if top_lines else "_No outbound stock movements in the last 7 days._")
    )
    title = f"Weekly Summary — {datetime.now(timezone.utc).date().isoformat()}"
    rep = Report(tenant_id=tenant_id, type="weekly_summary", title=title, content_md=md)
    db.add(rep)
    db.add(AutomationLog(
        tenant_id=tenant_id, job_name=JOB_NAME, status="success",
        outcome={"report_id": None, "low_stock": low_stock, "pending_pos": pending_pos, "sales_value": sales_value},
    ))
    await db.commit()
    await db.refresh(rep)
