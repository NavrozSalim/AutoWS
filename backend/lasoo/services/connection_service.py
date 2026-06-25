"""Connection lifecycle: connect, update, test, switch-to-production."""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..checklist import is_staging_complete, normalize_checklist
from ..errors import LasooError
from ..models import (
    ConnectionStatus,
    Environment,
    LasooListing,
    ListingStatus,
    MarketplaceConnection,
)
from ..lasoo_queries import build_payload
from . import crypto
from .client import LasooClient

logger = logging.getLogger("lasoo")


def _get_owned(user, connection_id: int) -> MarketplaceConnection:
    return get_object_or_404(
        MarketplaceConnection, id=connection_id, user=user, marketplace_name="lasoo"
    )


def list_connections(user):
    return list(
        MarketplaceConnection.objects.filter(user=user, marketplace_name="lasoo")
    )


def get_connection(user, connection_id: int) -> MarketplaceConnection:
    return _get_owned(user, connection_id)


def create_connection(user, payload) -> MarketplaceConnection:
    if not (payload.staging_auth_key or "").strip():
        raise LasooError("Staging AuthKey is required.")
    if not (payload.staging_base_url or "").strip():
        raise LasooError("Staging API base URL is required.")

    endpoints = payload.endpoints.dict() if payload.endpoints else {}

    conn = MarketplaceConnection(
        user=user,
        store_name=payload.store_name.strip(),
        retailer_name=(payload.retailer_name or "").strip(),
        contact_email=(payload.contact_email or "").strip(),
        staging_base_url=payload.staging_base_url.strip(),
        production_base_url=(payload.production_base_url or "").strip(),
        endpoints_json={k: v for k, v in endpoints.items() if v},
        staging_auth_key_encrypted=crypto.encrypt(payload.staging_auth_key.strip()),
        environment=Environment.STAGING,
        active_auth_key_type=Environment.STAGING,
        status=ConnectionStatus.CONNECTED_STAGING,
    )
    if payload.production_auth_key:
        conn.production_auth_key_encrypted = crypto.encrypt(
            payload.production_auth_key.strip()
        )

    checklist = normalize_checklist(None)
    checklist["staging_auth_key_connected"] = True
    conn.staging_checklist_json = checklist
    conn.save()
    logger.info("Created Lasoo connection store=%s user=%s", conn.store_name, user.pk)
    return conn


def update_connection(user, connection_id: int, payload) -> MarketplaceConnection:
    conn = _get_owned(user, connection_id)

    if payload.store_name is not None:
        conn.store_name = payload.store_name.strip()
    if payload.retailer_name is not None:
        conn.retailer_name = payload.retailer_name.strip()
    if payload.contact_email is not None:
        conn.contact_email = payload.contact_email.strip()
    if payload.staging_base_url is not None:
        conn.staging_base_url = payload.staging_base_url.strip()
    if payload.production_base_url is not None:
        conn.production_base_url = payload.production_base_url.strip()
    if payload.endpoints is not None:
        conn.endpoints_json = {k: v for k, v in payload.endpoints.dict().items() if v}

    # Only overwrite keys when a new non-empty value is provided.
    if payload.staging_auth_key:
        conn.staging_auth_key_encrypted = crypto.encrypt(payload.staging_auth_key.strip())
        checklist = normalize_checklist(conn.staging_checklist_json)
        checklist["staging_auth_key_connected"] = True
        conn.staging_checklist_json = checklist
    if payload.production_auth_key:
        conn.production_auth_key_encrypted = crypto.encrypt(
            payload.production_auth_key.strip()
        )

    conn.save()
    return conn


def test_connection(user, connection_id: int) -> dict:
    conn = _get_owned(user, connection_id)
    environment = conn.active_auth_key_type
    client = LasooClient(conn, environment, require_auth=False)

    # Core_TestNoAuthentication does not require auth in the body.
    payload = build_payload("test")
    result = client.send("test", payload)

    conn.last_tested_at = timezone.now()
    if result.ok:
        conn.error_message = ""
    else:
        conn.error_message = result.message
    conn.save(update_fields=["last_tested_at", "error_message", "updated_at"])

    return {
        "ok": result.ok,
        "message": result.message or ("Connection successful." if result.ok else ""),
        "environment": environment,
        "status": result.status,
    }


def switch_to_production(user, connection_id: int) -> MarketplaceConnection:
    conn = _get_owned(user, connection_id)

    if not conn.has_production_key:
        raise LasooError("Add a Production AuthKey before switching to production.")
    if not conn.production_base_url:
        raise LasooError("Add a Production API base URL before switching to production.")
    if not is_staging_complete(conn.staging_checklist_json):
        raise LasooError("Complete all staging checklist steps before switching.")

    conn.active_auth_key_type = Environment.PRODUCTION
    conn.environment = Environment.PRODUCTION
    conn.status = ConnectionStatus.CONNECTED_PRODUCTION
    conn.save(
        update_fields=["active_auth_key_type", "environment", "status", "updated_at"]
    )
    logger.info("Switched store=%s to production", conn.store_name)
    return conn


def set_checklist_item(user, connection_id: int, key: str, done: bool) -> MarketplaceConnection:
    conn = _get_owned(user, connection_id)
    checklist = normalize_checklist(conn.staging_checklist_json)
    if key not in checklist:
        raise LasooError(f"Unknown checklist item: {key}")
    checklist[key] = done
    conn.staging_checklist_json = checklist
    if is_staging_complete(checklist) and conn.status == ConnectionStatus.CONNECTED_STAGING:
        conn.status = ConnectionStatus.STAGING_COMPLETED
    conn.save(update_fields=["staging_checklist_json", "status", "updated_at"])
    return conn


def mark_checklist_auto(conn: MarketplaceConnection, key: str):
    """Flip an auto checklist step to True without overwriting manual progress."""
    checklist = normalize_checklist(conn.staging_checklist_json)
    if not checklist.get(key):
        checklist[key] = True
        conn.staging_checklist_json = checklist
        if (
            is_staging_complete(checklist)
            and conn.status == ConnectionStatus.CONNECTED_STAGING
        ):
            conn.status = ConnectionStatus.STAGING_COMPLETED
        conn.save(update_fields=["staging_checklist_json", "status", "updated_at"])
