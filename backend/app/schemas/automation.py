from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AutomationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_name: str
    status: str
    outcome: dict
    ts: datetime


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    content_md: str
    created_at: datetime


class DashboardSummary(BaseModel):
    total_products: int
    low_stock_count: int
    expired_count: int
    top_movers: list[dict]
    pending_po_count: int
