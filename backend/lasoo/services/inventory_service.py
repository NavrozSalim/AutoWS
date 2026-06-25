"""Inventory/price update flow.

Lets a user update price and stock for products that were *already created* for
a store, by uploading a small file of (SKU, Updated Price, Updated Stock).

Validation rules:
- SKU is required.
- Updated Price must be a number >= 0.
- Updated Stock must be a whole number >= 0.
- No duplicate SKUs within the file.
- The SKU must already exist for this store (created in the past).

On confirm, valid rows update the local listing and are pushed to Lasoo via the
existing ``Variants_BulkUpsert`` call (full variant body, with the new price and
stock merged in).
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..errors import LasooError
from ..models import (
    Environment,
    LasooListing,
    ListingStatus,
    MarketplaceConnection,
)
from ..utils import inventory_import
from . import listing_service, mapper
from .client import LasooClient

logger = logging.getLogger("lasoo")

# Listings the user has actually sent to Lasoo at least once.
_UPLOADED_STATUSES = {
    ListingStatus.UPLOADED_STAGING,
    ListingStatus.MAPPED,
    ListingStatus.UPLOADED_PRODUCTION,
}


def _get_connection(user, connection_id: int) -> MarketplaceConnection:
    return get_object_or_404(
        MarketplaceConnection, id=connection_id, user=user, marketplace_name="lasoo"
    )


def _parse_price(value):
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if price < 0:
        return None
    return price


def _parse_stock(value):
    text = str(value).strip()
    if text == "":
        return None
    try:
        # Reject decimals like "5.5" for stock; allow "5" and "5.0".
        stock = int(float(text))
        if float(text) != stock:
            return None
    except (TypeError, ValueError):
        return None
    if stock < 0:
        return None
    return stock


def _evaluate_rows(user, conn: MarketplaceConnection, rows: list[dict]) -> list[dict]:
    """Validate each parsed row against the rules and the store's listings."""
    # Map existing SKUs (for the store's active environment) -> listing.
    existing = {
        l.sku.strip().lower(): l
        for l in LasooListing.objects.filter(
            user=user, connection=conn, environment=conn.environment
        )
        if l.sku
    }

    results = []
    for row in rows:
        sku = (row.get("sku") or "").strip()
        errors: list[str] = []

        if not sku:
            errors.append("SKU is required.")

        price = _parse_price(row.get("updated_price"))
        if price is None:
            errors.append("Updated Price must be a number of 0 or more.")

        stock = _parse_stock(row.get("updated_stock"))
        if stock is None:
            errors.append("Updated Stock must be a whole number of 0 or more.")

        if row.get("duplicate"):
            errors.append(
                f"Duplicate SKU in file (first seen on row {row.get('duplicate_of_row')})."
            )

        listing = existing.get(sku.lower()) if sku else None
        if sku and listing is None:
            errors.append("This SKU was not created for this store. Create it first.")
        elif listing is not None and listing.status not in _UPLOADED_STATUSES:
            errors.append(
                "This product has not been uploaded to Lasoo yet. Upload it before updating."
            )

        old_price = float(listing.sale_price) if listing else None
        old_stock = listing.inventory if listing else None

        results.append(
            {
                "row_number": row.get("row_number"),
                "sku": sku,
                "updated_price": str(row.get("updated_price", "")),
                "updated_stock": str(row.get("updated_stock", "")),
                "old_price": old_price,
                "old_stock": old_stock,
                "found": listing is not None,
                "valid": not errors,
                "errors": errors,
                "updated": False,
                "_listing_id": listing.id if listing else None,
                "_price": price,
                "_stock": stock,
            }
        )

    return results


def _public_rows(results: list[dict]) -> list[dict]:
    """Strip internal fields (prefixed with _) before returning to the client."""
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]


def _summary(conn: MarketplaceConnection, results: list[dict], updated: int) -> dict:
    valid = sum(1 for r in results if r["valid"])
    return {
        "total_rows": len(results),
        "valid": valid,
        "invalid": len(results) - valid,
        "updated": updated,
        "environment": conn.environment,
        "rows": _public_rows(results),
    }


def preview(user, connection_id: int, filename: str, content: bytes) -> dict:
    """Validate the uploaded file without making any changes."""
    conn = _get_connection(user, connection_id)
    rows = inventory_import.parse_upload(filename, content)
    if not rows:
        raise LasooError("No data rows found in the uploaded file.")
    results = _evaluate_rows(user, conn, rows)
    return _summary(conn, results, updated=0)


@transaction.atomic
def apply_updates(
    user, connection_id: int, filename: str, content: bytes, update_valid_only: bool
) -> dict:
    """Validate, then update valid rows locally and push them to Lasoo."""
    conn = _get_connection(user, connection_id)
    rows = inventory_import.parse_upload(filename, content)
    if not rows:
        raise LasooError("No data rows found in the uploaded file.")

    results = _evaluate_rows(user, conn, rows)

    invalid = [r for r in results if not r["valid"]]
    if invalid and not update_valid_only:
        return {
            **_summary(conn, results, updated=0),
            "ok": False,
            "message": (
                f"{len(invalid)} row(s) have errors. Fix them, or choose "
                "'Update valid rows only'."
            ),
        }

    to_update = [r for r in results if r["valid"]]
    if not to_update:
        return {
            **_summary(conn, results, updated=0),
            "ok": False,
            "message": "No valid rows to update.",
        }

    environment = conn.active_auth_key_type
    client = LasooClient(conn, environment)

    listings_by_id = {
        l.id: l
        for l in LasooListing.objects.filter(
            id__in=[r["_listing_id"] for r in to_update]
        )
    }

    variants = []
    ordered_listings = []
    for r in to_update:
        listing = listings_by_id[r["_listing_id"]]
        listing.sale_price = r["_price"]
        listing.inventory = r["_stock"]
        listing.infinite_quantity = False
        # Keep existing original price; never let sale exceed it.
        if listing.original_price < listing.sale_price:
            listing.original_price = listing.sale_price

        data = listing_service._listing_to_data(listing)
        variants.append(data)
        ordered_listings.append((listing, r))

    payload = mapper.build_bulk_upsert_payload(variants, client.auth_key)
    result = client.send("bulk_upsert", payload)

    now = timezone.now()
    request_for_storage = {**payload, "auth": "***"}

    if result.ok:
        for listing, r in ordered_listings:
            listing.sale_price_cents = mapper.dollars_to_cents(listing.sale_price)
            listing.original_price_cents = mapper.dollars_to_cents(listing.original_price)
            listing.lasoo_request_json = request_for_storage
            listing.lasoo_response_json = result.data
            listing.last_uploaded_at = now
            listing.save(
                update_fields=[
                    "sale_price",
                    "inventory",
                    "infinite_quantity",
                    "sale_price_cents",
                    "original_price",
                    "original_price_cents",
                    "lasoo_request_json",
                    "lasoo_response_json",
                    "last_uploaded_at",
                    "updated_at",
                ]
            )
            r["updated"] = True
        updated_count = len(ordered_listings)
        message = (
            f"Updated {updated_count} product(s) on {environment}."
            if not invalid
            else f"Updated {updated_count} valid product(s); skipped {len(invalid)} with errors."
        )
    else:
        conn.error_message = result.message
        conn.save(update_fields=["error_message", "updated_at"])
        return {
            **_summary(conn, results, updated=0),
            "ok": False,
            "message": result.message or "Lasoo rejected the update.",
        }

    return {
        **_summary(conn, results, updated=updated_count),
        "ok": True,
        "message": message,
    }
