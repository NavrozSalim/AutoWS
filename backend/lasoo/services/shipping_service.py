"""Send shipping/tracking info to Lasoo via Shipments_Upsert and search shipments.

Lasoo's shipment API:
- ``Shipments_Upsert`` (/Shipments/Upsert/1.0.0): create/update a shipment with
  tracking number, carrier, status and the items that were shipped.
- ``Shipments_Search`` (/Shipments/Search/1.0.0): look up shipments for an invoice.

There is no separate "complete" endpoint; marking complete is an upsert with
``status = "DELIVERED"``.
"""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ..lasoo_queries import build_payload
from ..errors import LasooError
from ..models import LasooOrder, LasooShipment, OrderStatus
from . import connection_service
from .client import LasooClient

logger = logging.getLogger("lasoo")


def _get_order(user, order_id: int) -> LasooOrder:
    return get_object_or_404(LasooOrder, id=order_id, user=user)


def _invoice_id(order: LasooOrder):
    """Lasoo expects a numeric invoiceId; fall back to the raw string if needed."""
    for candidate in (order.external_order_key, order.lasoo_invoice_number):
        text = str(candidate or "").strip()
        if text.isdigit():
            return int(text)
    return order.external_order_key or order.lasoo_invoice_number


def _to_iso(value: str) -> str:
    """Convert a date or datetime string to an ISO 8601 timestamp."""
    if not value:
        return timezone.now().isoformat()
    dt = parse_datetime(value)
    if dt is None:
        d = parse_date(value)
        if d is not None:
            dt = timezone.datetime(d.year, d.month, d.day)
    if dt is None:
        return timezone.now().isoformat()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt.isoformat()


def _shipped_items(order: LasooOrder) -> list[dict]:
    """Build Lasoo ``shippedItems`` from the order's stored line items."""
    items = order.line_items_json
    if not isinstance(items, list):
        return []

    shipped = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        shipped.append(
            {
                "quantity": raw.get("quantity") or raw.get("qty") or 1,
                "lineItemId": (
                    raw.get("lineItemId") or raw.get("id") or raw.get("lineId")
                ),
                "externalProductKey": (
                    raw.get("externalProductKey") or raw.get("productKey") or ""
                ),
                "externalVariantKey": (
                    raw.get("externalVariantKey") or raw.get("variantKey") or ""
                ),
            }
        )
    return shipped


def _upsert(client: LasooClient, order: LasooOrder, *, tracking_number, carrier,
            tracking_url, dispatched_at_iso, status, note=""):
    data = {
        "invoiceId": _invoice_id(order),
        "shipmentTrackingNumber": tracking_number,
        "shipmentCarrier": carrier,
        "dispatchedAt": dispatched_at_iso,
        "note": note,
        "status": status,
        "shippedItems": _shipped_items(order),
        "shipmentTrackingLink": tracking_url,
    }
    payload = build_payload("shipping", data=data, auth=client.auth_key)
    return payload, client.send("shipping", payload)


def update(user, payload) -> dict:
    order = _get_order(user, payload.order_id)
    conn = order.connection
    environment = order.environment
    client = LasooClient(conn, environment)

    shipped_at = None
    if payload.shipped_date:
        shipped_at = parse_datetime(payload.shipped_date) or None
        if shipped_at is None:
            d = parse_date(payload.shipped_date)
            if d is not None:
                shipped_at = timezone.datetime(d.year, d.month, d.day)

    status = (getattr(payload, "status", "") or "OUT_FOR_DELIVERY").strip()

    shipment = LasooShipment.objects.create(
        order=order,
        tracking_number=(payload.tracking_number or "").strip(),
        carrier=(payload.carrier or "").strip(),
        tracking_url=(payload.tracking_url or "").strip(),
        shipped_at=shipped_at,
        status="submitted",
    )

    api_payload, result = _upsert(
        client,
        order,
        tracking_number=shipment.tracking_number,
        carrier=shipment.carrier,
        tracking_url=shipment.tracking_url,
        dispatched_at_iso=_to_iso(payload.shipped_date),
        status=status,
    )

    shipment.lasoo_request_json = {**api_payload, "auth": "***"}
    shipment.lasoo_response_json = result.data if result.ok else result.error
    shipment.status = "submitted" if result.ok else "failed"
    shipment.save(
        update_fields=["lasoo_request_json", "lasoo_response_json", "status"]
    )

    if result.ok:
        order.shipping_status = "submitted"
        order.status = OrderStatus.SHIPPING_SUBMITTED
        order.save(update_fields=["shipping_status", "status", "updated_at"])
        connection_service.mark_checklist_auto(conn, "shipping_info_sent")

    return {
        "ok": result.ok,
        "message": result.message or ("Shipping info sent." if result.ok else ""),
        "shipment_id": shipment.id,
    }


def complete(user, payload) -> dict:
    """Mark a shipment delivered (Shipments_Upsert with status DELIVERED)."""
    order = _get_order(user, payload.order_id)
    conn = order.connection
    environment = order.environment
    client = LasooClient(conn, environment)

    last = order.shipments.first()  # ordered by -created_at
    tracking_number = last.tracking_number if last else ""
    carrier = last.carrier if last else ""
    tracking_url = last.tracking_url if last else ""

    api_payload, result = _upsert(
        client,
        order,
        tracking_number=tracking_number,
        carrier=carrier,
        tracking_url=tracking_url,
        dispatched_at_iso=_to_iso(""),
        status="DELIVERED",
        note="Marked complete from Leeso",
    )

    if result.ok:
        order.shipping_status = "complete"
        order.status = OrderStatus.SHIPPING_COMPLETE
        order.save(update_fields=["shipping_status", "status", "updated_at"])
        connection_service.mark_checklist_auto(conn, "shipping_marked_complete")
        if last:
            last.status = "complete"
            last.lasoo_response_json = result.data
            last.save(update_fields=["status", "lasoo_response_json"])

    return {
        "ok": result.ok,
        "message": result.message
        or ("Shipping marked complete." if result.ok else ""),
    }


def search(user, order_id: int) -> dict:
    """Look up shipments for an order's invoice via Shipments_Search."""
    order = _get_order(user, order_id)
    conn = order.connection
    environment = order.environment
    client = LasooClient(conn, environment)

    data = {"invoiceId": _invoice_id(order)}
    last = order.shipments.first()
    if last and last.pk:
        data["shipmentId"] = last.pk

    payload = build_payload("shipments_search", data=data, auth=client.auth_key)
    result = client.send("shipments_search", payload)

    return {
        "ok": result.ok,
        "message": result.message or ("Shipments retrieved." if result.ok else ""),
        "data": result.data if result.ok else None,
    }
