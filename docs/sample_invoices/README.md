# Sample invoices

This folder is where the two test invoices live. They are not committed as binaries because the
project ships a generator script — run it once after cloning to populate this folder.

```bash
pip install Pillow
python docs/generate_sample_invoices.py
```

That produces:
- `invoice_01.png` — Krishna Distributors, 4 line items
- `invoice_02.png` — Bharat FMCG, 5 line items

Both are plain-text invoice layouts on a white background so any vision LLM (Gemini, GPT-4o) or
OCR engine (Tesseract) can extract the fields cleanly.

You can also upload any real supplier invoice (JPG, PNG, PDF) to `/invoices` in the app.
