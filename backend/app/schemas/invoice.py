from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ParsedLineItem(BaseModel):
    name: str
    qty: float
    unit_price: float
    total: float
    matched_product_id: int | None = None


class ParsedInvoice(BaseModel):
    supplier_name: str | None = None
    invoice_date: date | None = None
    line_items: list[ParsedLineItem] = []
    grand_total: float | None = None
    notes: str | None = None


class InvoiceParseResponse(BaseModel):
    invoice_id: int
    parsed: ParsedInvoice


class ReceiveLineItem(BaseModel):
    product_id: int
    qty: int = Field(gt=0)
    unit_price: float = Field(gt=0)


class ReceiveRequest(BaseModel):
    invoice_id: int | None = None
    supplier_id: int | None = None
    lines: list[ReceiveLineItem] = Field(min_length=1)


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int | None
    raw_path: str
    parsed_json: dict
    confirmed: bool
    created_at: datetime
