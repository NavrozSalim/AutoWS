"""Staging checklist definition and helpers.

The checklist gates the transition from staging to production. Some steps are
flipped automatically by the system (e.g. after a successful upload), others are
manual (Lasoo-side actions like mapping variants and approval).
"""

# Ordered list of (key, human label, is_auto) for the 8 staging steps.
CHECKLIST_STEPS = [
    ("staging_auth_key_connected", "Staging AuthKey connected", True),
    ("variants_uploaded", "Variants uploaded", True),
    ("lasoo_mapped_variants", "Lasoo mapped variants to products", False),
    ("test_orders_created", "Test orders created", False),
    ("invoices_retrieved", "Invoices/orders retrieved", True),
    ("shipping_info_sent", "Shipping information sent", True),
    ("shipping_marked_complete", "Shipping marked complete", True),
    ("approved_for_production", "Approved for production", False),
]

CHECKLIST_KEYS = [key for key, _, _ in CHECKLIST_STEPS]
MANUAL_KEYS = {key for key, _, is_auto in CHECKLIST_STEPS if not is_auto}


def default_checklist() -> dict:
    return {key: False for key in CHECKLIST_KEYS}


def normalize_checklist(value: dict | None) -> dict:
    """Ensure all keys exist (handles new keys added over time)."""
    base = default_checklist()
    if value:
        for key in CHECKLIST_KEYS:
            base[key] = bool(value.get(key, False))
    return base


def is_staging_complete(checklist: dict | None) -> bool:
    normalized = normalize_checklist(checklist)
    return all(normalized.values())


def checklist_with_labels(checklist: dict | None) -> list[dict]:
    """Return checklist as an ordered list with labels for the UI."""
    normalized = normalize_checklist(checklist)
    return [
        {
            "key": key,
            "label": label,
            "auto": is_auto,
            "done": normalized[key],
        }
        for key, label, is_auto in CHECKLIST_STEPS
    ]
