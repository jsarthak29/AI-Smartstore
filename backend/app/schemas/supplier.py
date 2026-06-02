from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    categories: list[str] = []
    lead_time_days: int = Field(ge=0, default=7)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    categories: list[str] | None = None
    lead_time_days: int | None = Field(default=None, ge=0)


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
