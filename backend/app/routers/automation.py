from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_tenant_id, require_admin
from app.database import get_db
from app.models.automation_log import AutomationLog
from app.models.product import Product
from app.models.purchase_order import POStatus, PurchaseOrder
from app.models.report import Report
from app.models.stock_movement import StockMovement
from app.schemas.automation import AutomationLogOut, DashboardSummary, ReportOut
from app.services.scheduler import run_job_now

router = APIRouter(tags=["automation"])


@router.get("/automation/logs", response_model=list[AutomationLogOut])
async def list_logs(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    rows = (await db.execute(
        select(AutomationLog).where(AutomationLog.tenant_id == tenant_id).order_by(AutomationLog.ts.desc()).limit(100)
    )).scalars().all()
    return rows


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    rows = (await db.execute(
        select(Report).where(Report.tenant_id == tenant_id).order_by(Report.created_at.desc()).limit(50)
    )).scalars().all()
    return rows


@router.post("/automation/run/{job_name}", dependencies=[Depends(require_admin)])
async def run_now(job_name: str):
    try:
        await run_job_now(job_name)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True, "job": job_name}


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    total = (await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    )).scalar_one()
    low = (await db.execute(
        select(func.count(Product.id)).where(and_(
            Product.tenant_id == tenant_id, Product.is_active.is_(True),
            Product.stock < Product.reorder_threshold,
        ))
    )).scalar_one()
    today = date.today()
    expired = (await db.execute(
        select(func.count(Product.id)).where(and_(
            Product.tenant_id == tenant_id, Product.is_active.is_(True),
            Product.expiry_date.is_not(None), Product.expiry_date <= today,
        ))
    )).scalar_one()
    pending = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(and_(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status.in_([POStatus.DRAFT.value, POStatus.SENT.value, POStatus.ACKNOWLEDGED.value]),
        ))
    )).scalar_one()
    # top movers — last 30 days by outflow volume
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
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
    top = []
    for pid, vol in movers:
        p = (await db.execute(select(Product).where(Product.id == pid))).scalar_one_or_none()
        if p:
            top.append({"id": p.id, "name": p.name, "sku": p.sku, "volume": int(vol)})
    return DashboardSummary(
        total_products=total,
        low_stock_count=low,
        expired_count=expired,
        top_movers=top,
        pending_po_count=pending,
    )
