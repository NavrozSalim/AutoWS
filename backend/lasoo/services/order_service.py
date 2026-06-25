"""Retrieve and persist orders/invoices from Lasoo."""
import logging

from django.shortcuts import get_object_or_404

from ..models import LasooOrder, MarketplaceConnection, OrderStatus
from ..lasoo_queries import build_payload
from . import connection_service
from .client import LasooClient

logger = logging.getLogger("lasoo")


def _get_connection(user, connection_id: int) -> MarketplaceConnection:
    return get_object_or_404(
        MarketplaceConnection, id=connection_id, user=user, marketplace_name="lasoo"
    )


def fetch(user, connection_id: int, page: int = 1, take: int = 50) -> dict:
    conn = _get_connection(user, connection_id)
    environment = conn.active_auth_key_type
    client = LasooClient(conn, environment)

    # Invoices_Search: pull invoices with line items, customer and shipping info.
    payload = build_payload(
        "orders",
        data={
            "page": page,
            "take": take,
            "includeLineItems": True,
            "includeCustomer": True,
            "includeShipping": True,
            "includeInvoice": True,
        },
        auth=client.auth_key,
    )
    result = client.send("orders", payload)
    if not result.ok:
        return {"ok": False, "message": result.message, "orders": []}

    raw_orders = _extract_orders(result.data)
    saved = []
    for raw in raw_orders:
        if not isinstance(raw, dict):
            continue
        order = _upsert_order(user, conn, environment, raw)
        saved.append(order)

    if saved:
        connection_service.mark_checklist_auto(conn, "invoices_retrieved")

    return {
        "ok": True,
        "message": f"Retrieved {len(saved)} order(s) from {environment}.",
        "orders": [_serialize(o) for o in saved],
    }


def create_test_order(user, connection_id: int) -> dict:
    """Ask Lasoo to create a test order (staging only) so the flow can be tested."""
    conn = _get_connection(user, connection_id)
    environment = conn.active_auth_key_type
    client = LasooClient(conn, environment)

    payload = build_payload("create_test_order", data={}, auth=client.auth_key)
    result = client.send("create_test_order", payload)
    if not result.ok:
        return {"ok": False, "message": result.message}

    # Best-effort: persist any returned order so it shows up immediately.
    for raw in _extract_orders(result.data):
        if isinstance(raw, dict):
            _upsert_order(user, conn, environment, raw)

    return {
        "ok": True,
        "message": "Test order created. Click 'Fetch from Lasoo' to load it.",
    }


def list_orders(user, connection_id: int):
    conn = _get_connection(user, connection_id)
    return list(LasooOrder.objects.filter(user=user, connection=conn))


def _extract_orders(data) -> list[dict]:
    """Dig through Lasoo's response envelope to find the list of invoices.

    Lasoo wraps payloads like ``{"results": {"body": {"invoices": [...]}}}`` so we
    recurse through the common container keys until we hit a list of dicts.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in (
            "invoices",
            "orders",
            "items",
            "records",
            "results",
            "body",
            "data",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _extract_orders(value)
                if nested:
                    return nested
    return []


def _upsert_order(user, conn, environment, raw: dict) -> LasooOrder:
    invoice_id = (
        raw.get("id")
        or raw.get("invoiceId")
        or raw.get("invoiceNumber")
        or raw.get("externalOrderKey")
        or raw.get("orderKey")
    )
    order_key = str(invoice_id or "")
    invoice_number = str(
        raw.get("invoiceNumber") or raw.get("invoice") or invoice_id or ""
    )
    defaults = {
        "lasoo_invoice_number": invoice_number,
        "customer_info_json": raw.get("customer") or raw.get("customerInfo"),
        "line_items_json": (
            raw.get("lineItems") or raw.get("items") or raw.get("products")
        ),
        "total_amount_cents": _to_cents(
            raw.get("totalCents")
            or raw.get("total")
            or raw.get("totalAmount")
            or raw.get("grandTotal")
        ),
        "status": _map_status(raw.get("status")),
        "lasoo_response_json": raw,
    }
    order, _ = LasooOrder.objects.update_or_create(
        user=user,
        connection=conn,
        external_order_key=order_key,
        environment=environment,
        defaults=defaults,
    )
    return order


def _to_cents(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int,)):
            return value
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None


def _map_status(raw_status) -> str:
    if not raw_status:
        return OrderStatus.NEW
    text = str(raw_status).strip().lower()
    mapping = {
        "new": OrderStatus.NEW,
        "paid": OrderStatus.PAID,
        "cancelled": OrderStatus.CANCELLED,
        "canceled": OrderStatus.CANCELLED,
        "refunded": OrderStatus.REFUNDED,
        "sent": OrderStatus.SENT,
        "shipped": OrderStatus.SENT,
        "out_for_delivery": OrderStatus.SHIPPING_SUBMITTED,
        "delivered": OrderStatus.SHIPPING_COMPLETE,
    }
    return mapping.get(text, OrderStatus.NEW)


def _serialize(order: LasooOrder) -> dict:
    return {
        "id": order.id,
        "lasoo_invoice_number": order.lasoo_invoice_number,
        "external_order_key": order.external_order_key,
        "customer_info_json": order.customer_info_json,
        "line_items_json": order.line_items_json,
        "status": order.status,
        "shipping_status": order.shipping_status,
        "total_amount_cents": order.total_amount_cents,
        "environment": order.environment,
    }
