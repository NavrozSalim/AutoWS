"""Ninja (Pydantic) request/response schemas. Secrets are never echoed back."""
from typing import Optional

from ninja import Schema


class EndpointsConfig(Schema):
    test: Optional[str] = None
    bulk_upsert: Optional[str] = None
    bulk_delete: Optional[str] = None
    variants_search: Optional[str] = None
    orders: Optional[str] = None
    create_test_order: Optional[str] = None
    shipping: Optional[str] = None
    shipments_search: Optional[str] = None
    # Kept for backward-compatibility with older saved connections.
    shipping_complete: Optional[str] = None


class ConnectIn(Schema):
    store_name: str
    staging_base_url: str
    staging_auth_key: str
    production_base_url: Optional[str] = None
    production_auth_key: Optional[str] = None
    retailer_name: Optional[str] = None
    contact_email: Optional[str] = None
    endpoints: Optional[EndpointsConfig] = None


class ConnectionUpdateIn(Schema):
    store_name: Optional[str] = None
    staging_base_url: Optional[str] = None
    staging_auth_key: Optional[str] = None
    production_base_url: Optional[str] = None
    production_auth_key: Optional[str] = None
    retailer_name: Optional[str] = None
    contact_email: Optional[str] = None
    endpoints: Optional[EndpointsConfig] = None


class ChecklistItem(Schema):
    key: str
    label: str
    auto: bool
    done: bool


class ConnectionOut(Schema):
    id: int
    store_name: str
    retailer_name: str
    contact_email: str
    environment: str
    active_auth_key_type: str
    status: str
    status_label: str
    staging_base_url: str
    production_base_url: str
    endpoints: dict
    has_staging_key: bool
    has_production_key: bool
    staging_key_masked: str
    production_key_masked: str
    checklist: list[ChecklistItem]
    staging_complete: bool
    last_tested_at: Optional[str] = None
    error_message: str


class ChecklistUpdateIn(Schema):
    key: str
    done: bool


class ListingIn(Schema):
    product_key: str = ""
    variant_key: str = ""
    title: str = ""
    description: str = ""
    brand: str = ""
    category: Optional[str] = ""
    sku: str = ""
    barcode: Optional[str] = ""
    image_urls: str = ""
    inventory: int = 0
    infinite_quantity: bool = False
    original_price: float = 0
    sale_price: float = 0


class ListingOut(Schema):
    id: int
    connection_id: int
    external_product_key: str
    external_variant_key: str
    title: str
    description: str
    brand: str
    category: str
    sku: str
    barcode: str
    image_urls: str
    inventory: int
    infinite_quantity: bool
    original_price: float
    sale_price: float
    original_price_cents: int
    sale_price_cents: int
    environment: str
    status: str
    status_label: str
    validation_errors: Optional[list] = None
    last_uploaded_at: Optional[str] = None


class ShippingUpdateIn(Schema):
    order_id: int
    tracking_number: str
    carrier: str
    tracking_url: Optional[str] = ""
    shipped_date: Optional[str] = ""
    status: Optional[str] = "OUT_FOR_DELIVERY"


class ShippingCompleteIn(Schema):
    order_id: int


class MessageOut(Schema):
    ok: bool
    message: str = ""
