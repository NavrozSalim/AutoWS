"""Convert Book4.xlsx eBay export into Lasoo bulk-upload catalog CSV."""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

import pandas as pd

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


def html_to_text(html: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", html or "")
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_brand(html: str, text: str) -> str:
    for source in (html, text):
        match = re.search(
            r"ux-labels-values--brand[\s\S]{0,400}?ux-textspans\">([^<]+)",
            source,
            re.IGNORECASE,
        )
        if match:
            brand = match.group(1).strip()
            if brand.lower() not in {"brand", "new", "new:"}:
                return brand
    return "UNHO"


def collect_images(row: pd.Series) -> str:
    urls = []
    for i in range(1, 9):
        url = str(row.get(f"Image {i:02d}", "")).strip()
        if url:
            urls.append(url)
    return "|".join(urls)


def to_money(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def convert_row(row: pd.Series) -> dict:
    sku = str(row.get("SKU", "")).strip()
    title = str(row.get("title", "")).strip()
    product_key = sku or title[:40]
    variant_key = sku or product_key

    vendor_price = row.get("Vendor Price", "")
    final_price = row.get("Final Price", "")
    # Final Price = retail/list price; Vendor Price = your sale price.
    original = to_money(final_price if str(final_price).strip() else vendor_price)
    sale = to_money(vendor_price if str(vendor_price).strip() else final_price)
    if float(sale) > float(original):
        original, sale = sale, original

    inventory = str(row.get("Vendor Ivnentory", "") or row.get("Vendor Inventory", "")).strip()
    if not inventory.isdigit():
        inventory = "0"

    html_desc = str(row.get("eBay Main Description", ""))
    description = html_to_text(html_desc)
    if not description:
        description = title

    specifics_html = str(row.get("Item Specifics - HTML", ""))
    specifics_text = str(row.get("Item Specifics - Text", ""))

    return {
        "Product Key": product_key,
        "Variant Key": variant_key,
        "Title": title,
        "Description": description,
        "Brand": extract_brand(specifics_html, specifics_text),
        "Category": str(row.get("Categories", "")).strip(),
        "SKU": sku,
        "Barcode": str(row.get("UPC", "")).strip(),
        "Image URLs": collect_images(row),
        "Inventory": inventory,
        "Infinite Quantity": "false",
        "Original Price": original,
        "Sale Price": sale,
    }


def convert_file(source: Path, dest: Path) -> int:
    df = pd.read_excel(source, dtype=str).fillna("")
    records = [convert_row(row) for _, row in df.iterrows() if any(str(v).strip() for v in row.values)]
    out = pd.DataFrame(records, columns=TEMPLATE_HEADERS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False, encoding="utf-8-sig")
    return len(records)


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"c:\Users\Navroz\Downloads\Book4.xlsx")
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else source.with_name("lasoo-catalog-book4.csv")
    count = convert_file(source, dest)
    print(f"Wrote {count} row(s) to {dest}")


if __name__ == "__main__":
    main()
