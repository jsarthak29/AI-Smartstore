from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_movement import StockMovement


async def compute_forecast(db: AsyncSession, tenant_id: int, product_id: int, horizon_days: int = 7) -> dict:
    """7-day demand forecast using a 14-day simple moving average over outbound stock movements.

    Rationale (also covered in README): the SKU-level dataset for a small retailer is too thin for
    ARIMA / Prophet to outperform a naive baseline, and SMA is interpretable to the store owner.
    """
    window_days = 14
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (await db.execute(
        select(StockMovement).where(and_(
            StockMovement.tenant_id == tenant_id,
            StockMovement.product_id == product_id,
            StockMovement.ts >= cutoff,
        ))
    )).scalars().all()

    daily_outflow: dict[date, int] = defaultdict(int)
    for r in rows:
        if r.delta < 0:  # outbound = demand
            daily_outflow[r.ts.date()] += -r.delta

    today = date.today()
    if daily_outflow:
        total_demand = sum(daily_outflow.values())
        days_with_data = (today - min(daily_outflow.keys())).days + 1
        avg = total_demand / max(days_with_data, 1)
        history_days = days_with_data
        method = f"sma_{window_days}d"
    else:
        avg = 0.0
        history_days = 0
        method = "fallback_zero"

    points = []
    for i in range(1, horizon_days + 1):
        points.append({"date": today + timedelta(days=i), "predicted_demand": round(avg, 2)})
    return {
        "product_id": product_id,
        "method": method,
        "history_days_used": history_days,
        "points": points,
    }
