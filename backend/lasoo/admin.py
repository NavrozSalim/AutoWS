from django.contrib import admin

from .models import LasooListing, LasooOrder, LasooShipment, MarketplaceConnection


@admin.register(MarketplaceConnection)
class MarketplaceConnectionAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "environment", "status", "created_at")
    list_filter = ("environment", "status")
    search_fields = ("store_name", "user__username")
    # Never expose encrypted secrets in admin forms.
    exclude = ("staging_auth_key_encrypted", "production_auth_key_encrypted")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LasooListing)
class LasooListingAdmin(admin.ModelAdmin):
    list_display = ("external_variant_key", "title", "user", "status", "environment")
    list_filter = ("status", "environment")
    search_fields = ("external_variant_key", "sku", "title")


@admin.register(LasooOrder)
class LasooOrderAdmin(admin.ModelAdmin):
    list_display = ("external_order_key", "lasoo_invoice_number", "status", "shipping_status")
    list_filter = ("status", "shipping_status", "environment")


@admin.register(LasooShipment)
class LasooShipmentAdmin(admin.ModelAdmin):
    list_display = ("tracking_number", "carrier", "order", "status", "created_at")
