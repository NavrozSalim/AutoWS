"""Delete variants from Lasoo (Variants_BulkDelete) and coordinate with local DB."""
import logging

from ..errors import LasooError
from ..lasoo_queries import build_payload
from ..models import Environment, LasooListing, ListingStatus, MarketplaceConnection
from .client import LasooClient

logger = logging.getLogger("lasoo")

# Listings in these statuses were pushed to Lasoo and should be removed there too.
UPLOADED_STATUSES = frozenset(
    {
        ListingStatus.UPLOADED_STAGING,
        ListingStatus.MAPPED,
        ListingStatus.UPLOADED_PRODUCTION,
    }
)


def _delete_key(listing: LasooListing) -> dict:
    return {
        "externalProductKey": listing.external_product_key,
        "externalVariantKey": listing.external_variant_key,
    }


def _dedupe_keys(keys: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for key in keys:
        token = (key["externalProductKey"], key["externalVariantKey"])
        if token in seen:
            continue
        seen.add(token)
        unique.append(key)
    return unique


def environments_for_listing(listing: LasooListing) -> list[str]:
    """Lasoo environments where this listing may exist."""
    if listing.status not in UPLOADED_STATUSES:
        return []
    if listing.status == ListingStatus.UPLOADED_PRODUCTION:
        return [Environment.PRODUCTION]
    return [Environment.STAGING]


def _delete_keys_on_lasoo(
    conn: MarketplaceConnection, environment: str, keys: list[dict]
) -> None:
    if not keys:
        return
    client = LasooClient(conn, environment)
    payload = build_payload(
        "bulk_delete",
        data={"keys": keys},
        auth=client.auth_key,
    )
    result = client.send("bulk_delete", payload)
    if not result.ok:
        raise LasooError(
            result.message
            or f"Failed to delete {len(keys)} variant(s) from Lasoo ({environment})."
        )
    logger.info(
        "Deleted %s variant(s) from Lasoo store=%s env=%s",
        len(keys),
        conn.store_name,
        environment,
    )


def delete_listing_from_lasoo(listing: LasooListing) -> bool:
    """Remove a single listing from Lasoo if it was uploaded. Returns True if Lasoo was called."""
    conn = listing.connection
    keys_by_env: dict[str, list[dict]] = {}
    for env in environments_for_listing(listing):
        keys_by_env.setdefault(env, []).append(_delete_key(listing))

    if not keys_by_env:
        return False

    for env, keys in keys_by_env.items():
        _delete_keys_on_lasoo(conn, env, _dedupe_keys(keys))
    return True


def delete_listings_from_lasoo(
    conn: MarketplaceConnection, listings: list[LasooListing]
) -> int:
    """Bulk-delete uploaded listings from Lasoo. Returns count removed on Lasoo."""
    keys_by_env: dict[str, list[dict]] = {}
    lasoo_count = 0

    for listing in listings:
        if listing.status not in UPLOADED_STATUSES:
            continue
        lasoo_count += 1
        for env in environments_for_listing(listing):
            keys_by_env.setdefault(env, []).append(_delete_key(listing))

    for env, keys in keys_by_env.items():
        _delete_keys_on_lasoo(conn, env, _dedupe_keys(keys))

    return lasoo_count
