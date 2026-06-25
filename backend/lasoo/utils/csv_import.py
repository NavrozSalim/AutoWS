"""Parse uploaded CSV / Excel listing templates into normalized row dicts."""
import io

import pandas as pd

# Maps human template headers -> internal field names.
COLUMN_MAP = {
    "product key": "product_key",
    "variant key": "variant_key",
    "title": "title",
    "description": "description",
    "brand": "brand",
    "category": "category",
    "sku": "sku",
    "barcode": "barcode",
    "image urls": "image_urls",
    "image url": "image_urls",
    "inventory": "inventory",
    "infinite quantity": "infinite_quantity",
    "original price": "original_price",
    "sale price": "sale_price",
}

TEMPLATE_HEADERS = [
    "Product Key",
    "Variant Key",
    "Title",
    "Description",
    "Brand",
    "Category",
    "SKU",
    "Barcode",
    "Image URLs",
    "Inventory",
    "Infinite Quantity",
    "Original Price",
    "Sale Price",
]

_TRUE_VALUES = {"true", "1", "yes", "y", "t"}


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE_VALUES


def parse_upload(filename: str, content: bytes) -> list[dict]:
    """Return a list of row dicts (1-based 'row_number' included)."""
    name = (filename or "").lower()
    buffer = io.BytesIO(content)
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buffer, dtype=str)
    else:
        df = pd.read_csv(buffer, dtype=str, encoding="utf-8-sig")

    df = df.fillna("")
    rows = []
    for idx, raw in enumerate(df.to_dict(orient="records"), start=2):
        # start=2 because row 1 is the header in the user's file.
        normalized = {}
        for header, value in raw.items():
            key = COLUMN_MAP.get(str(header).strip().lower())
            if key:
                normalized[key] = str(value).strip()
        if not any(normalized.values()):
            continue
        normalized["infinite_quantity"] = _coerce_bool(
            normalized.get("infinite_quantity", "")
        )
        normalized["row_number"] = idx
        rows.append(normalized)
    return rows


def build_error_csv(rows: list[dict]) -> str:
    """Build a CSV string of rows + their validation errors."""
    records = []
    for row in rows:
        record = {h: row.get(COLUMN_MAP.get(h.lower(), ""), "") for h in TEMPLATE_HEADERS}
        record["Row"] = row.get("row_number", "")
        record["Errors"] = " | ".join(row.get("errors", []))
        records.append(record)
    df = pd.DataFrame(records, columns=["Row", *TEMPLATE_HEADERS, "Errors"])
    return df.to_csv(index=False)


def build_template_csv() -> str:
    sample = {
        "Product Key": "TSHIRT-001",
        "Variant Key": "TSHIRT-001-BLACK-M",
        "Title": "Black T-Shirt (M)",
        "Description": "Soft 100% cotton tee.",
        "Brand": "MyBrand",
        "Category": "Apparel > T-Shirts",
        "SKU": "TSHIRT-001-BLACK-M",
        "Barcode": "123456789012",
        "Image URLs": "https://img.example.com/a.jpg|https://img.example.com/b.jpg",
        "Inventory": "10",
        "Infinite Quantity": "false",
        "Original Price": "29.99",
        "Sale Price": "24.99",
    }
    df = pd.DataFrame([sample], columns=TEMPLATE_HEADERS)
    return df.to_csv(index=False)
