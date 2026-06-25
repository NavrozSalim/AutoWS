"""Convert ORM models into safe dicts for the API (masking secrets)."""
from .checklist import checklist_with_labels, is_staging_complete
from .models import ConnectionStatus, LasooListing, ListingStatus, MarketplaceConnection
from .services import crypto


def serialize_connection(conn: MarketplaceConnection) -> dict:
    return {
        "id": conn.id,
        "store_name": conn.store_name,
        "retailer_name": conn.retailer_name,
        "contact_email": conn.contact_email,
        "environment": conn.environment,
        "active_auth_key_type": conn.active_auth_key_type,
        "status": conn.status,
        "status_label": ConnectionStatus(conn.status).label,
        "staging_base_url": conn.staging_base_url,
        "production_base_url": conn.production_base_url,
        "endpoints": conn.endpoints(),
        "has_staging_key": conn.has_staging_key,
        "has_production_key": conn.has_production_key,
        "staging_key_masked": crypto.mask_encrypted(conn.staging_auth_key_encrypted),
        "production_key_masked": crypto.mask_encrypted(conn.production_auth_key_encrypted),
        "checklist": checklist_with_labels(conn.staging_checklist_json),
        "staging_complete": is_staging_complete(conn.staging_checklist_json),
        "last_tested_at": conn.last_tested_at.isoformat() if conn.last_tested_at else None,
        "error_message": conn.error_message,
    }


def serialize_listing(listing: LasooListing) -> dict:
    return {
        "id": listing.id,
        "connection_id": listing.connection_id,
        "external_product_key": listing.external_product_key,
        "external_variant_key": listing.external_variant_key,
        "title": listing.title,
        "description": listing.description,
        "brand": listing.brand,
        "category": listing.category,
        "sku": listing.sku,
        "barcode": listing.barcode,
        "image_urls": listing.image_urls,
        "inventory": listing.inventory,
        "infinite_quantity": listing.infinite_quantity,
        "original_price": float(listing.original_price),
        "sale_price": float(listing.sale_price),
        "original_price_cents": listing.original_price_cents,
        "sale_price_cents": listing.sale_price_cents,
        "environment": listing.environment,
        "status": listing.status,
        "status_label": ListingStatus(listing.status).label,
        "validation_errors": listing.validation_errors_json,
        "last_uploaded_at": listing.last_uploaded_at.isoformat()
        if listing.last_uploaded_at
        else None,
    }
