from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class POLineIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0)
    unit_price: float | None = Field(default=None, gt=0)


class POLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    qty: int
    unit_price: float


class POCreate(BaseModel):
    supplier_id: int
    lines: list[POLineIn] = Field(min_length=1)
    notes: str | None = None


class POStatusUpdate(BaseModel):
    status: Literal["draft", "sent", "acknowledged", "received"]


class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int
    status: str
    total: float
    notes: str | None
    created_by: int
    created_at: datetime
    sent_at: datetime | None
    lines: list[POLineOut]
