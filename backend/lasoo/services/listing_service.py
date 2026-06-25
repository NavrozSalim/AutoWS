"""Listing CRUD, validation, CSV import, and uploads to staging/production."""
import logging
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..checklist import is_staging_complete
from ..errors import LasooError
from ..models import (
    ConnectionStatus,
    Environment,
    LasooListing,
    ListingStatus,
    MarketplaceConnection,
)
from ..utils import csv_import
from . import connection_service, crypto, mapper, validator
from .client import LasooClient
from . import variant_delete_service

logger = logging.getLogger("lasoo")


def _get_connection(user, connection_id: int) -> MarketplaceConnection:
    return get_object_or_404(
        MarketplaceConnection, id=connection_id, user=user, marketplace_name="lasoo"
    )


def _get_listing(user, listing_id: int) -> LasooListing:
    return get_object_or_404(LasooListing, id=listing_id, user=user)


def _apply_fields(listing: LasooListing, data: dict):
    product_key, variant_key = mapper.resolve_keys(data)
    listing.external_product_key = product_key
    listing.external_variant_key = variant_key
    listing.title = (data.get("title") or "").strip()
    listing.description = (data.get("description") or "").strip()
    listing.brand = (data.get("brand") or "").strip()
    listing.category = (data.get("category") or "").strip()
    listing.sku = (data.get("sku") or "").strip()
    listing.barcode = (data.get("barcode") or "").strip()
    listing.image_urls = mapper.normalize_image_urls(data.get("image_urls"))
    listing.infinite_quantity = bool(data.get("infinite_quantity"))
    try:
        listing.inventory = 0 if listing.infinite_quantity else int(data.get("inventory") or 0)
    except (TypeError, ValueError):
        listing.inventory = 0
    listing.original_price = _safe_decimal(data.get("original_price"))
    listing.sale_price = _safe_decimal(data.get("sale_price"))


def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _finalize_validation(listing: LasooListing, data: dict):
    errors = validator.validate_listing(data)
    if errors:
        listing.validation_errors_json = errors
        listing.status = ListingStatus.VALIDATION_FAILED
        listing.external_data_object_json = ""
        listing.original_price_cents = 0
        listing.sale_price_cents = 0
    else:
        listing.validation_errors_json = None
        listing.original_price_cents = mapper.dollars_to_cents(data.get("original_price"))
        listing.sale_price_cents = mapper.dollars_to_cents(data.get("sale_price"))
        listing.external_data_object_json = mapper.build_external_data_object(data)
        listing.status = ListingStatus.READY
    return errors


def create(user, connection_id: int, payload) -> LasooListing:
    conn = _get_connection(user, connection_id)
    data = payload.dict()
    listing = LasooListing(user=user, connection=conn, environment=conn.environment)
    _apply_fields(listing, data)
    _finalize_validation(listing, data)
    listing.save()
    return listing


def update(user, listing_id: int, payload) -> LasooListing:
    listing = _get_listing(user, listing_id)
    data = payload.dict()
    _apply_fields(listing, data)
    _finalize_validation(listing, data)
    listing.save()
    return listing


def delete(user, listing_id: int) -> dict:
    listing = _get_listing(user, listing_id)
    variant_key = listing.external_variant_key
    removed_from_lasoo = variant_delete_service.delete_listing_from_lasoo(listing)
    listing.delete()
    if removed_from_lasoo:
        message = f'Product "{variant_key}" deleted from AutoWS and Lasoo.'
    else:
        message = f'Product "{variant_key}" deleted from AutoWS.'
    return {"ok": True, "message": message}


def get(user, listing_id: int) -> LasooListing:
    return _get_listing(user, listing_id)


def list_for_user(user, connection_id: int | None = None, status: str | None = None):
    qs = LasooListing.objects.filter(user=user)
    if connection_id:
        qs = qs.filter(connection_id=connection_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def _listing_to_data(listing: LasooListing) -> dict:
    return {
        "product_key": listing.external_product_key,
        "variant_key": listing.external_variant_key,
        "title": listing.title,
        "description": listing.description,
        "brand": listing.brand,
        "category": listing.category,
        "sku": listing.sku,
        "barcode": listing.barcode,
        "image_urls": listing.image_urls,
        "inventory": listing.inventory,
        "infinite_quantity": listing.infinite_quantity,
        "original_price": listing.original_price,
        "sale_price": listing.sale_price,
    }


def validate_all(user, connection_id: int) -> dict:
    conn = _get_connection(user, connection_id)
    listings = LasooListing.objects.filter(user=user, connection=conn)
    valid, invalid = 0, 0
    for listing in listings:
        data = _listing_to_data(listing)
        errors = _finalize_validation(listing, data)
        listing.save(
            update_fields=[
                "validation_errors_json",
                "status",
                "original_price_cents",
                "sale_price_cents",
                "external_data_object_json",
                "updated_at",
            ]
        )
        if errors:
            invalid += 1
        else:
            valid += 1
    return {"valid": valid, "invalid": invalid, "total": valid + invalid}


def bulk_import(user, connection_id: int, filename: str, content: bytes, upload_valid_only: bool):
    conn = _get_connection(user, connection_id)
    rows = csv_import.parse_upload(filename, content)
    if not rows:
        raise LasooError("No data rows found in the uploaded file.")

    preview, created = [], 0
    for row in rows:
        errors = validator.validate_listing(row)
        row_result = {
            "row_number": row.get("row_number"),
            "sku": row.get("sku", ""),
            "variant_key": row.get("variant_key", ""),
            "errors": errors,
            "valid": not errors,
            "imported": False,
        }
        if errors and upload_valid_only:
            preview.append(row_result)
            continue
        if errors and not upload_valid_only:
            preview.append(row_result)
            continue

        # Valid row -> upsert listing by (connection, variant_key, environment).
        product_key, variant_key = mapper.resolve_keys(row)
        listing, _ = LasooListing.objects.get_or_create(
            user=user,
            connection=conn,
            external_variant_key=variant_key,
            environment=conn.environment,
            defaults={
                "external_product_key": product_key,
                "title": "",
                "description": "",
                "brand": "",
                "sku": row.get("sku", ""),
                "image_urls": "",
                "original_price": Decimal("0"),
                "sale_price": Decimal("0"),
            },
        )
        _apply_fields(listing, row)
        _finalize_validation(listing, row)
        listing.save()
        created += 1
        row_result["imported"] = True
        preview.append(row_result)

    return {
        "total_rows": len(rows),
        "imported": created,
        "rows": preview,
    }


def _require_ready(listings):
    if not listings:
        raise LasooError("No listings are ready to upload. Validate them first.")


@transaction.atomic
def upload(user, connection_id: int, environment: str) -> dict:
    conn = _get_connection(user, connection_id)

    if environment == Environment.PRODUCTION:
        if not is_staging_complete(conn.staging_checklist_json):
            raise LasooError(
                "Complete the staging checklist before uploading to production."
            )
        if not conn.has_production_key or not conn.production_base_url:
            raise LasooError("Configure production AuthKey and base URL first.")

    # Upload listings that belong to this connection and are READY (or previously
    # uploaded to staging when going to production).
    if environment == Environment.STAGING:
        listings = list(
            LasooListing.objects.filter(
                user=user, connection=conn, status=ListingStatus.READY
            )
        )
    else:
        listings = list(
            LasooListing.objects.filter(
                user=user,
                connection=conn,
                status__in=[
                    ListingStatus.READY,
                    ListingStatus.UPLOADED_STAGING,
                    ListingStatus.MAPPED,
                ],
            )
        )
    _require_ready(listings)

    client = LasooClient(conn, environment)
    variants = [_listing_to_data(l) for l in listings]
    payload = mapper.build_bulk_upsert_payload(variants, client.auth_key)
    result = client.send("bulk_upsert", payload)

    now = timezone.now()
    request_for_storage = {**payload, "auth": "***"}  # never persist the raw key

    if result.ok:
        new_status = (
            ListingStatus.UPLOADED_PRODUCTION
            if environment == Environment.PRODUCTION
            else ListingStatus.UPLOADED_STAGING
        )
        for listing in listings:
            listing.status = new_status
            listing.lasoo_request_json = request_for_storage
            listing.lasoo_response_json = result.data
            listing.last_uploaded_at = now
            listing.save(
                update_fields=[
                    "status",
                    "lasoo_request_json",
                    "lasoo_response_json",
                    "last_uploaded_at",
                    "updated_at",
                ]
            )
        if environment == Environment.STAGING:
            connection_service.mark_checklist_auto(conn, "variants_uploaded")
    else:
        for listing in listings:
            listing.status = ListingStatus.FAILED
            listing.lasoo_request_json = request_for_storage
            listing.lasoo_response_json = result.error
            listing.save(
                update_fields=[
                    "status",
                    "lasoo_request_json",
                    "lasoo_response_json",
                    "updated_at",
                ]
            )
        conn.error_message = result.message
        conn.save(update_fields=["error_message", "updated_at"])

    return {
        "ok": result.ok,
        "message": result.message
        or (f"Uploaded {len(listings)} variants to {environment}." if result.ok else ""),
        "uploaded": len(listings) if result.ok else 0,
        "environment": environment,
    }
