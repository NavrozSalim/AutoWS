"""HTTP client for the LasooConnect API.

Built per-connection (not from env): base URL, endpoint paths and AuthKey all
come from the MarketplaceConnection row, so multiple stores can each use their
own configuration. Logs requests/responses but never logs the AuthKey.
"""
import logging

import httpx
from django.conf import settings

from ..errors import LasooError
from ..lasoo_queries import extract_lasoo_failure_message
from ..models import Environment, MarketplaceConnection
from . import crypto

logger = logging.getLogger("lasoo")


class LasooResult:
    def __init__(self, ok: bool, data=None, error=None, message: str = "", status: int = 0):
        self.ok = ok
        self.data = data
        self.error = error
        self.message = message
        self.status = status

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "status": self.status,
        }


class LasooClient:
    def __init__(
        self,
        connection: MarketplaceConnection,
        environment: str,
        *,
        require_auth: bool = True,
    ):
        self.connection = connection
        self.environment = environment
        self.base_url = connection.base_url_for(environment)
        self.endpoints = connection.endpoints()
        self._auth_key = ""

        if not self.base_url:
            raise LasooError(
                f"No {environment} base URL configured for store "
                f"'{connection.store_name}'. Add it in connection settings."
            )

        encrypted = (
            connection.production_auth_key_encrypted
            if environment == Environment.PRODUCTION
            else connection.staging_auth_key_encrypted
        )
        if encrypted:
            self._auth_key = crypto.decrypt(encrypted)
        elif require_auth:
            raise LasooError(
                f"No {environment} AuthKey configured for store "
                f"'{connection.store_name}'."
            )

    def url(self, endpoint_key: str) -> str:
        path = self.endpoints.get(endpoint_key, "")
        if not path:
            raise LasooError(f"Endpoint '{endpoint_key}' is not configured.")
        return f"{self.base_url.rstrip('/')}{path}"

    @property
    def auth_key(self) -> str:
        return self._auth_key

    def send(self, endpoint_key: str, payload: dict) -> LasooResult:
        url = self.url(endpoint_key)
        # Strip auth before logging.
        safe_payload = {k: v for k, v in payload.items() if k != "auth"}
        logger.info(
            "Lasoo request store=%s env=%s endpoint=%s query=%s",
            self.connection.store_name,
            self.environment,
            endpoint_key,
            payload.get("query"),
        )
        logger.debug("Lasoo request body: %s", safe_payload)

        try:
            resp = httpx.post(url, json=payload, timeout=settings.LASOO_TIMEOUT)
        except httpx.RequestError as exc:
            logger.error("Lasoo connection error endpoint=%s: %s", endpoint_key, exc)
            return LasooResult(
                ok=False,
                error=str(exc),
                message="Could not reach Lasoo. Please try again.",
                status=0,
            )

        body = _safe_body(resp)
        if resp.is_success:
            failure = extract_lasoo_failure_message(body)
            if failure:
                logger.error(
                    "Lasoo business error store=%s status=%s body=%s",
                    self.connection.store_name,
                    resp.status_code,
                    body,
                )
                return LasooResult(
                    ok=False,
                    data=body,
                    error=body,
                    message=failure,
                    status=resp.status_code,
                )
            logger.info(
                "Lasoo response store=%s status=%s ok",
                self.connection.store_name,
                resp.status_code,
            )
            message = _success_message(body)
            return LasooResult(ok=True, data=body, message=message, status=resp.status_code)

        logger.error(
            "Lasoo API error store=%s status=%s body=%s",
            self.connection.store_name,
            resp.status_code,
            body,
        )
        return LasooResult(
            ok=False,
            error=body,
            message=_user_message(body, resp.status_code),
            status=resp.status_code,
        )


def _safe_body(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return {"raw": resp.text[:2000]}


def _user_message(body, status: int) -> str:
    if isinstance(body, dict):
        for field in ("message", "error", "detail", "title"):
            if body.get(field):
                return str(body[field])
    return f"Lasoo returned an error (HTTP {status})."


def _success_message(body) -> str:
    if isinstance(body, dict):
        if body.get("success") is True:
            msg = body.get("message")
            if isinstance(msg, str) and msg.strip() and msg.strip().lower() != "no message":
                return msg.strip()
            return "Connection successful."
    return "Connection successful."
