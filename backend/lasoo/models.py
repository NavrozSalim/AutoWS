from django.conf import settings
from django.db import models

from .checklist import default_checklist
from .lasoo_queries import DEFAULT_ENDPOINTS


class Environment(models.TextChoices):
    STAGING = "staging", "Staging"
    PRODUCTION = "production", "Production"


class ConnectionStatus(models.TextChoices):
    PENDING = "pending", "Not Connected"
    CONNECTED_STAGING = "connected_staging", "Connected to Staging"
    STAGING_COMPLETED = "staging_completed", "Staging Completed"
    CONNECTED_PRODUCTION = "connected_production", "Connected to Production"
    FAILED = "failed", "Failed"
    DISCONNECTED = "disconnected", "Disconnected"


class ListingStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    VALIDATION_FAILED = "validation_failed", "Validation Failed"
    READY = "ready", "Ready to Upload"
    UPLOADED_STAGING = "uploaded_staging", "Uploaded to Staging"
    MAPPED = "mapped", "Mapped by Lasoo"
    UPLOADED_PRODUCTION = "uploaded_production", "Uploaded to Production"
    FAILED = "failed", "Failed"


class OrderStatus(models.TextChoices):
    NEW = "new", "New"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"
    SENT = "sent", "Sent"
    SHIPPING_SUBMITTED = "shipping_submitted", "Shipping Submitted"
    SHIPPING_COMPLETE = "shipping_complete", "Shipping Complete"
class MarketplaceConnection(models.Model):
    """A single Lasoo store connection owned by a user.

    Per-store config (base URLs, endpoint paths, AuthKeys) lives here so that
    one user can connect multiple stores, each with independent settings.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_connections",
    )
    marketplace_name = models.CharField(max_length=50, default="lasoo")
    store_name = models.CharField(max_length=255)
    retailer_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")

    environment = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.STAGING
    )
    active_auth_key_type = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.STAGING
    )

    # Per-store API configuration (entered in UI, not env).
    staging_base_url = models.URLField(blank=True, default="")
    production_base_url = models.URLField(blank=True, default="")
    endpoints_json = models.JSONField(default=dict, blank=True)

    # Encrypted secrets - never returned to the frontend in plaintext.
    staging_auth_key_encrypted = models.TextField(blank=True, default="")
    production_auth_key_encrypted = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=30, choices=ConnectionStatus.choices, default=ConnectionStatus.PENDING
    )
    staging_checklist_json = models.JSONField(default=default_checklist)

    last_tested_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "marketplace_name"])]

    def __str__(self):
        return f"{self.store_name} ({self.environment})"

    @property
    def has_staging_key(self) -> bool:
        return bool(self.staging_auth_key_encrypted)

    @property
    def has_production_key(self) -> bool:
        return bool(self.production_auth_key_encrypted)

    def endpoints(self) -> dict:
        merged = dict(DEFAULT_ENDPOINTS)
        if self.endpoints_json:
            merged.update({k: v for k, v in self.endpoints_json.items() if v})
        # Upgrade saved paths from earlier app versions to the confirmed Lasoo
        # paths. Each key maps the wrong/old value -> correct default key.
        legacy_paths = {
            "bulk_upsert": {"/Variants_BulkUpsert"},
            "test": {"/TestConnection"},
            "orders": {"/Invoices_Get", "/Invoices/Get/1.0.0"},
            "shipping": {"/Shipping_Update", "/Shipping/Update/1.0.0"},
        }
        for key, old_values in legacy_paths.items():
            if merged.get(key) in old_values:
                merged[key] = DEFAULT_ENDPOINTS[key]
        # The old "Shipping_Complete" endpoint no longer exists in Lasoo; drop it
        # so it can't be sent by mistake.
        if merged.get("shipping_complete") in {
            "/Shipping_Complete",
            "/Shipping/Complete/1.0.0",
        }:
            merged.pop("shipping_complete", None)
        return merged

    def base_url_for(self, environment: str) -> str:
        return (
            self.production_base_url
            if environment == Environment.PRODUCTION
            else self.staging_base_url
        )


class LasooListing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    connection = models.ForeignKey(
        MarketplaceConnection, on_delete=models.CASCADE, related_name="listings"
    )

    external_product_key = models.CharField(max_length=255)
    external_variant_key = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    description = models.TextField()
    brand = models.CharField(max_length=255)
    category = models.CharField(max_length=500, blank=True, default="")
    sku = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255, blank=True, default="")
    image_urls = models.TextField()  # pipe-joined: a|b|c
    inventory = models.IntegerField(default=0)
    infinite_quantity = models.BooleanField(default=False)
    original_price = models.DecimalField(max_digits=12, decimal_places=2)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    original_price_cents = models.IntegerField(default=0)
    sale_price_cents = models.IntegerField(default=0)
    external_data_object_json = models.TextField(blank=True, default="")

    environment = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.STAGING
    )
    status = models.CharField(
        max_length=30, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )
    validation_errors_json = models.JSONField(null=True, blank=True)
    lasoo_request_json = models.JSONField(null=True, blank=True)
    lasoo_response_json = models.JSONField(null=True, blank=True)
    last_uploaded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "external_variant_key", "environment"],
                name="uniq_variant_per_connection_env",
            )
        ]

    def __str__(self):
        return f"{self.external_variant_key} - {self.title}"


class LasooOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    connection = models.ForeignKey(
        MarketplaceConnection, on_delete=models.CASCADE, related_name="orders"
    )

    lasoo_invoice_number = models.CharField(max_length=255, blank=True, default="")
    external_order_key = models.CharField(max_length=255, blank=True, default="")
    customer_info_json = models.JSONField(null=True, blank=True)
    line_items_json = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=OrderStatus.choices, default=OrderStatus.NEW
    )
    shipping_status = models.CharField(max_length=30, default="pending")
    total_amount_cents = models.IntegerField(null=True, blank=True)
    lasoo_response_json = models.JSONField(null=True, blank=True)
    environment = models.CharField(
        max_length=20, choices=Environment.choices, default=Environment.STAGING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "external_order_key", "environment"],
                name="uniq_order_per_connection_env",
            )
        ]

    def __str__(self):
        return self.lasoo_invoice_number or self.external_order_key or str(self.pk)


class LasooShipment(models.Model):
    order = models.ForeignKey(
        LasooOrder, on_delete=models.CASCADE, related_name="shipments"
    )
    tracking_number = models.CharField(max_length=255, blank=True, default="")
    carrier = models.CharField(max_length=255, blank=True, default="")
    tracking_url = models.URLField(blank=True, default="")
    shipped_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, default="pending")
    lasoo_request_json = models.JSONField(null=True, blank=True)
    lasoo_response_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shipment {self.tracking_number} for order {self.order_id}"
