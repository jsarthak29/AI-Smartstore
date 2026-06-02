import logging
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_log import AutomationLog
from app.models.product import Product
from app.models.report import Report
from app.models.tenant import Tenant

log = logging.getLogger(__name__)

JOB_NAME = "expiry_agent"


def _suggested_action(days_left: int) -> str:
    if days_left < 0:
        return "Write off (already expired)"
    if days_left <= 3:
        return "Aggressive discount or write-off"
    if days_left <= 7:
        return "Apply 20% discount"
    return "Promote / bundle deal"


async def run(db: AsyncSession) -> None:
    tenants = (await db.execute(select(Tenant))).scalars().all()
    for t in tenants:
        try:
            await _run_for_tenant(db, t.id)
        except Exception as e:
            log.exception("expiry_agent failed for tenant %s", t.id)
            db.add(AutomationLog(tenant_id=t.id, job_name=JOB_NAME, status="error", outcome={"error": str(e)}))
            await db.commit()


async def _run_for_tenant(db: AsyncSession, tenant_id: int) -> None:
    horizon = date.today() + timedelta(days=14)
    rows = (await db.execute(
        select(Product).where(and_(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.expiry_date.is_not(None),
            Product.expiry_date <= horizon,
        ))
    )).scalars().all()

    if not rows:
        db.add(AutomationLog(
            tenant_id=tenant_id, job_name=JOB_NAME, status="success",
            outcome={"expiring_count": 0},
        ))
        await db.commit()
        return

    lines = ["| SKU | Product | Stock | Expiry | Days Left | Suggested Action |", "|---|---|---|---|---|---|"]
    for p in rows:
        days_left = (p.expiry_date - date.today()).days
        lines.append(f"| {p.sku} | {p.name} | {p.stock} | {p.expiry_date} | {days_left} | {_suggested_action(days_left)} |")

    md = (
        f"# Expiry Alert — {date.today().isoformat()}\n\n"
        f"**{len(rows)} products** expire within 14 days.\n\n"
        + "\n".join(lines)
    )
    rep = Report(
        tenant_id=tenant_id, type="expiry_alert",
        title=f"Expiry Alert — {date.today().isoformat()}", content_md=md,
    )
    db.add(rep)
    db.add(AutomationLog(
        tenant_id=tenant_id, job_name=JOB_NAME, status="success",
        outcome={"expiring_count": len(rows)},
    ))
    await db.commit()
