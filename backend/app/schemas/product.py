from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=80)
    unit_price: float = Field(gt=0)
    reorder_threshold: int = Field(ge=0, default=10)
    expiry_date: date | None = None
    preferred_supplier_id: int | None = None


class ProductCreate(ProductBase):
    stock: int = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    unit_price: float | None = Field(default=None, gt=0)
    reorder_threshold: int | None = Field(default=None, ge=0)
    expiry_date: date | None = None
    preferred_supplier_id: int | None = None
    stock: int | None = Field(default=None, ge=0)


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stock_status: Literal["ok", "low", "critical", "expired"] | None = None


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class ForecastPoint(BaseModel):
    date: date
    predicted_demand: float


class ForecastResponse(BaseModel):
    product_id: int
    method: str
    history_days_used: int
    points: list[ForecastPoint]
