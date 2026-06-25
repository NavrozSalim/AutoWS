"""Lasoo API routes (JWT-authenticated, scoped per user + connection)."""
import logging

from django.http import HttpResponse
from ninja import File, Query, Router
from ninja.files import UploadedFile
from ninja_jwt.authentication import JWTAuth

from .errors import LasooError

from .schemas import (
    ChecklistUpdateIn,
    ConnectIn,
    ConnectionOut,
    ConnectionUpdateIn,
    ListingIn,
    ListingOut,
    MessageOut,
    ShippingCompleteIn,
    ShippingUpdateIn,
)
from .serializers import serialize_connection, serialize_listing
from .services import (
    connection_service,
    inventory_service,
    listing_service,
    order_service,
    shipping_service,
)
from .utils import csv_import, inventory_import

logger = logging.getLogger("lasoo")

router = Router(auth=JWTAuth(), tags=["lasoo"])


# ── Connections ──
@router.get("/connections", response=list[ConnectionOut])
def list_connections(request):
    return [serialize_connection(c) for c in connection_service.list_connections(request.auth)]


@router.post("/connect", response=ConnectionOut)
def connect(request, payload: ConnectIn):
    conn = connection_service.create_connection(request.auth, payload)
    return serialize_connection(conn)


@router.get("/connections/{connection_id}", response=ConnectionOut)
def get_connection(request, connection_id: int):
    return serialize_connection(connection_service.get_connection(request.auth, connection_id))


@router.put("/connections/{connection_id}", response=ConnectionOut)
def update_connection(request, connection_id: int, payload: ConnectionUpdateIn):
    conn = connection_service.update_connection(request.auth, connection_id, payload)
    return serialize_connection(conn)


@router.post("/connections/{connection_id}/test-connection", response=MessageOut)
def test_connection(request, connection_id: int):
    return connection_service.test_connection(request.auth, connection_id)


@router.post("/connections/{connection_id}/checklist", response=ConnectionOut)
def update_checklist(request, connection_id: int, payload: ChecklistUpdateIn):
    conn = connection_service.set_checklist_item(
        request.auth, connection_id, payload.key, payload.done
    )
    return serialize_connection(conn)


@router.post("/connections/{connection_id}/switch-to-production", response=ConnectionOut)
def switch_to_production(request, connection_id: int):
    conn = connection_service.switch_to_production(request.auth, connection_id)
    return serialize_connection(conn)


# ── Listings ──
@router.get("/listings", response=list[ListingOut])
def list_listings(
    request,
    connection_id: int | None = Query(None),
    status: str | None = Query(None),
):
    listings = listing_service.list_for_user(request.auth, connection_id, status)
    return [serialize_listing(l) for l in listings]


@router.post("/connections/{connection_id}/listings/create", response=ListingOut)
def create_listing(request, connection_id: int, payload: ListingIn):
    return serialize_listing(listing_service.create(request.auth, connection_id, payload))


@router.get("/listings/{listing_id}", response=ListingOut)
def get_listing(request, listing_id: int):
    return serialize_listing(listing_service.get(request.auth, listing_id))


@router.put("/listings/{listing_id}", response=ListingOut)
def update_listing(request, listing_id: int, payload: ListingIn):
    return serialize_listing(listing_service.update(request.auth, listing_id, payload))


@router.delete("/listings/{listing_id}", response=MessageOut)
def delete_listing(request, listing_id: int):
    listing_service.delete(request.auth, listing_id)
    return {"ok": True, "message": "Listing deleted."}


@router.post("/connections/{connection_id}/listings/validate", response=MessageOut)
def validate_listings(request, connection_id: int):
    result = listing_service.validate_all(request.auth, connection_id)
    return {
        "ok": result["invalid"] == 0,
        "message": f"{result['valid']} valid, {result['invalid']} invalid of {result['total']}.",
    }


@router.post("/connections/{connection_id}/listings/bulk-upload")
def bulk_upload(
    request,
    connection_id: int,
    file: UploadedFile = File(...),
    upload_valid_only: bool = Query(False),
):
    try:
        content = file.read()
        return listing_service.bulk_import(
            request.auth, connection_id, file.name, content, upload_valid_only
        )
    except LasooError:
        raise
    except Exception as exc:
        logger.exception("Bulk upload failed connection=%s file=%s", connection_id, file.name)
        raise LasooError(
            "Could not process the uploaded file. Check the CSV format and try again."
        ) from exc


@router.post("/connections/{connection_id}/listings/upload-staging", response=MessageOut)
def upload_staging(request, connection_id: int):
    return listing_service.upload(request.auth, connection_id, "staging")


@router.post("/connections/{connection_id}/listings/upload-production", response=MessageOut)
def upload_production(request, connection_id: int):
    return listing_service.upload(request.auth, connection_id, "production")


@router.get("/listings-template.csv")
def download_template(request):
    csv_text = csv_import.build_template_csv()
    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="lasoo-listing-template.csv"'
    return response


# ── Inventory / price updates ──
@router.get("/inventory-template.csv")
def download_inventory_template(request):
    csv_text = inventory_import.build_template_csv()
    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="lasoo-inventory-template.csv"'
    )
    return response


@router.post("/connections/{connection_id}/inventory/preview")
def inventory_preview(request, connection_id: int, file: UploadedFile = File(...)):
    try:
        content = file.read()
        return inventory_service.preview(
            request.auth, connection_id, file.name, content
        )
    except LasooError:
        raise
    except Exception as exc:
        logger.exception(
            "Inventory preview failed connection=%s file=%s", connection_id, file.name
        )
        raise LasooError(
            "Could not read the uploaded file. Check the format and try again."
        ) from exc


@router.post("/connections/{connection_id}/inventory/update")
def inventory_update(
    request,
    connection_id: int,
    file: UploadedFile = File(...),
    update_valid_only: bool = Query(False),
):
    try:
        content = file.read()
        return inventory_service.apply_updates(
            request.auth, connection_id, file.name, content, update_valid_only
        )
    except LasooError:
        raise
    except Exception as exc:
        logger.exception(
            "Inventory update failed connection=%s file=%s", connection_id, file.name
        )
        raise LasooError(
            "Could not process the inventory update. Check the file and try again."
        ) from exc


# ── Orders ──
@router.get("/connections/{connection_id}/orders")
def get_orders(request, connection_id: int, refresh: bool = Query(False), page: int = 1):
    if refresh:
        return order_service.fetch(request.auth, connection_id, page)
    orders = order_service.list_orders(request.auth, connection_id)
    return {
        "ok": True,
        "message": "",
        "orders": [order_service._serialize(o) for o in orders],
    }


@router.post("/connections/{connection_id}/orders/create-test", response=MessageOut)
def create_test_order(request, connection_id: int):
    return order_service.create_test_order(request.auth, connection_id)


# ── Shipping ──
@router.post("/shipping/update", response=MessageOut)
def shipping_update(request, payload: ShippingUpdateIn):
    return shipping_service.update(request.auth, payload)


@router.post("/shipping/complete", response=MessageOut)
def shipping_complete(request, payload: ShippingCompleteIn):
    return shipping_service.complete(request.auth, payload)


@router.post("/shipping/search")
def shipping_search(request, payload: ShippingCompleteIn):
    return shipping_service.search(request.auth, payload.order_id)
