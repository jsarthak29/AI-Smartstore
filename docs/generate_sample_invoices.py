"""Generate two sample invoice PNGs in docs/sample_invoices/.

Run from the repo root:  python docs/generate_sample_invoices.py
Needs Pillow (pip install Pillow). The output PNGs are deliberately plain-text
on a white background so any vision LLM (or Tesseract) can read them.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent / "sample_invoices"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = ["arial.ttf", "DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_invoice(filename: str, supplier: str, date_str: str, lines: list[tuple[str, int, float]]) -> None:
    img = Image.new("RGB", (900, 1100), "white")
    d = ImageDraw.Draw(img)
    title_f = _font(34)
    h_f = _font(22)
    n_f = _font(18)

    d.text((40, 40), supplier, fill="black", font=title_f)
    d.text((40, 90), "Tax Invoice", fill="black", font=h_f)
    d.text((40, 130), f"Date: {date_str}", fill="black", font=n_f)
    d.text((40, 160), "Bill To: Raj Grocery, 14 Market Road", fill="black", font=n_f)

    # table header
    y = 230
    d.line([(40, y - 10), (860, y - 10)], fill="black", width=1)
    d.text((50, y), "Item", fill="black", font=h_f)
    d.text((420, y), "Qty", fill="black", font=h_f)
    d.text((540, y), "Unit Price", fill="black", font=h_f)
    d.text((740, y), "Total", fill="black", font=h_f)
    y += 40
    d.line([(40, y - 10), (860, y - 10)], fill="black", width=1)

    grand = 0.0
    for name, qty, unit in lines:
        total = qty * unit
        grand += total
        d.text((50, y), name, fill="black", font=n_f)
        d.text((420, y), str(qty), fill="black", font=n_f)
        d.text((540, y), f"{unit:.2f}", fill="black", font=n_f)
        d.text((740, y), f"{total:.2f}", fill="black", font=n_f)
        y += 36

    y += 20
    d.line([(40, y), (860, y)], fill="black", width=2)
    y += 20
    d.text((540, y), "Grand Total", fill="black", font=h_f)
    d.text((740, y), f"{grand:.2f}", fill="black", font=h_f)

    out = OUT_DIR / filename
    img.save(out)
    print(f"wrote {out}")


def main() -> None:
    make_invoice(
        "invoice_01.png",
        supplier="Krishna Distributors",
        date_str="2026-05-28",
        lines=[
            ("Basmati Rice 5kg", 20, 540.00),
            ("Wheat Flour 10kg", 10, 480.00),
            ("Sunflower Oil 1L", 30, 155.00),
            ("Iodised Salt 1kg", 50, 22.00),
        ],
    )
    make_invoice(
        "invoice_02.png",
        supplier="Bharat FMCG",
        date_str="2026-05-30",
        lines=[
            ("Marie Biscuits 200g", 60, 35.00),
            ("Potato Chips 100g", 80, 30.00),
            ("Cola 1L Bottle", 24, 70.00),
            ("Detergent Powder 1kg", 12, 220.00),
            ("Bath Soap 100g", 100, 45.00),
        ],
    )


if __name__ == "__main__":
    main()
