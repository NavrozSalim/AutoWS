"""Parse inventory-update files (SKU / Updated Price / Updated Stock).

This is a lighter workflow than the full catalog import: the user only provides
the SKU of a product that already exists for the store, plus its new price and
stock. Duplicate SKUs inside the file are flagged here at parse time.
"""
import io

import pandas as pd

# Maps human template headers -> internal field names. Accepts a few aliases so
# slightly different column names still work.
COLUMN_MAP = {
    "sku": "sku",
    "updated price": "updated_price",
    "posted price": "updated_price",
    "price": "updated_price",
    "updated stock": "updated_stock",
    "posted inventory": "updated_stock",
    "updated inventory": "updated_stock",
    "stock": "updated_stock",
    "inventory": "updated_stock",
}

TEMPLATE_HEADERS = ["SKU", "Updated Price", "Updated Stock"]


def parse_upload(filename: str, content: bytes) -> list[dict]:
    """Return a list of row dicts with a 1-based ``row_number``.

    Each row also gets a ``duplicate`` flag (True when its SKU already appeared
    on an earlier row in the same file).
    """
    name = (filename or "").lower()
    buffer = io.BytesIO(content)
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buffer, dtype=str)
    else:
        df = pd.read_csv(buffer, dtype=str, encoding="utf-8-sig")

    df = df.fillna("")
    rows: list[dict] = []
    seen_skus: dict[str, int] = {}

    for idx, raw in enumerate(df.to_dict(orient="records"), start=2):
        # start=2 because row 1 is the header in the user's file.
        normalized: dict = {}
        for header, value in raw.items():
            key = COLUMN_MAP.get(str(header).strip().lower())
            if key:
                normalized[key] = str(value).strip()

        if not any(normalized.values()):
            continue

        sku = (normalized.get("sku") or "").strip()
        normalized["sku"] = sku
        normalized["row_number"] = idx

        sku_lower = sku.lower()
        if sku and sku_lower in seen_skus:
            normalized["duplicate"] = True
            normalized["duplicate_of_row"] = seen_skus[sku_lower]
        else:
            normalized["duplicate"] = False
            if sku:
                seen_skus[sku_lower] = idx

        rows.append(normalized)

    return rows


def build_template_csv() -> str:
    sample = {
        "SKU": "TSHIRT-001-BLACK-M",
        "Updated Price": "24.99",
        "Updated Stock": "50",
    }
    df = pd.DataFrame([sample], columns=TEMPLATE_HEADERS)
    return df.to_csv(index=False)
