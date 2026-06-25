"""AES-256-GCM encryption for store AuthKeys + masking helpers.

The encryption key is app-wide (settings.LASOO_ENCRYPTION_KEY, base64 of 32
bytes). Each store's AuthKeys are encrypted at rest and never returned to the
frontend in plaintext - only a masked form like ``****abcd``.
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

from ..errors import LasooError

_NONCE_SIZE = 12


def _load_key() -> bytes:
    raw = settings.LASOO_ENCRYPTION_KEY
    if not raw:
        raise LasooError(
            "Server misconfiguration: LASOO_ENCRYPTION_KEY is not set.", status_code=500
        )
    try:
        key = base64.b64decode(raw)
    except Exception as exc:  # noqa: BLE001
        raise LasooError(
            "Server misconfiguration: LASOO_ENCRYPTION_KEY is not valid base64.",
            status_code=500,
        ) from exc
    if len(key) != 32:
        raise LasooError(
            "Server misconfiguration: LASOO_ENCRYPTION_KEY must decode to 32 bytes.",
            status_code=500,
        )
    return key


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        plaintext = ""
    key = _load_key()
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt(token: str) -> str:
    if not token:
        return ""
    key = _load_key()
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 4:
        return "****"
    return "****" + plaintext[-4:]


def mask_encrypted(token: str) -> str:
    """Decrypt just enough to produce a mask without exposing the full key."""
    if not token:
        return ""
    try:
        return mask_key(decrypt(token))
    except Exception:  # noqa: BLE001
        return "****"
