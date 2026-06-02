"""Invoice OCR via Gemini vision. Accepts a single uploaded file (image or PDF) and returns
structured JSON. For PDFs we rasterize the first page with pdf2image (requires poppler)."""
import io
import json
import logging
from pathlib import Path

import google.generativeai as genai
from PIL import Image

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

EXTRACTION_PROMPT = (
    "You are an expert at extracting structured data from supplier invoices.\n"
    "Return a JSON object with this exact shape (no commentary):\n"
    "{\n"
    "  \"supplier_name\": string | null,\n"
    "  \"invoice_date\": string (YYYY-MM-DD) | null,\n"
    "  \"line_items\": [ { \"name\": string, \"qty\": number, \"unit_price\": number, \"total\": number } ],\n"
    "  \"grand_total\": number | null,\n"
    "  \"notes\": string | null\n"
    "}\n"
    "If a field is illegible, set it to null. Quantities may be fractional. Strip currency symbols from numbers."
)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "supplier_name": {"type": "STRING"},
        "invoice_date": {"type": "STRING"},
        "line_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "qty": {"type": "NUMBER"},
                    "unit_price": {"type": "NUMBER"},
                    "total": {"type": "NUMBER"},
                },
            },
        },
        "grand_total": {"type": "NUMBER"},
        "notes": {"type": "STRING"},
    },
}


def _rasterize(path: Path) -> Image.Image:
    if path.suffix.lower() == ".pdf":
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(str(path), first_page=1, last_page=1, dpi=200)
            if not pages:
                raise ValueError("empty PDF")
            return pages[0]
        except Exception as e:
            log.exception("pdf rasterize failed")
            raise ValueError(f"could not rasterize PDF: {e}")
    return Image.open(str(path)).convert("RGB")


def _empty_result() -> dict:
    return {
        "supplier_name": None,
        "invoice_date": None,
        "line_items": [],
        "grand_total": None,
        "notes": "OCR unavailable (Gemini key not configured)",
    }


def parse_invoice(path: Path) -> dict:
    if not settings.GEMINI_API_KEY:
        log.warning("OCR called without GEMINI_API_KEY — returning empty stub")
        return _empty_result()
    img = _rasterize(path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        settings.GEMINI_VISION_MODEL,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        },
    )
    response = model.generate_content([
        EXTRACTION_PROMPT,
        {"mime_type": "image/png", "data": buf.getvalue()},
    ])
    raw = response.text or ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Gemini returned non-JSON: %s", raw[:300])
        return _empty_result()
    parsed.setdefault("line_items", [])
    return parsed
