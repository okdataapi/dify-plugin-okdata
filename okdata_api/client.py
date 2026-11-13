"""HTTP client for api.okdata.online, shared by the provider and every tool.

One request shape for everything: the key goes in `Authorization: Bearer`, the caller's
price cap in `X-Max-Price`, and every call carries `X-Source: dify` so usage can be
grouped by integration. Paid calls get an `Idempotency-Key`, reused by the single retry,
so a retried call is never billed twice.
"""

from __future__ import annotations

import math
import re
import time
import uuid
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

BASE_URL = "https://api.okdata.online"
SIGNUP_URL = "https://okdata.online/signup/?src=dify-plugin"
SOURCE_LABEL = "dify"
USER_AGENT = "okdata-dify-plugin/0.1.0"
KEY_PREFIX = "okd_"
CREDENTIAL_NAME = "okdata_api_key"

TIMEOUT_SECONDS = 60.0
MAX_RETRY_WAIT_SECONDS = 5.0
DEFAULT_RETRY_WAIT_SECONDS = 1.0
RETRYABLE = frozenset({"yes", "same_key"})
METHODS = frozenset({"GET", "POST"})
ENDPOINT_ID = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")
API_PATH = re.compile(r"^/v1/[a-z0-9_/]+$")
MAX_PRICE_CEILING = Decimal("100")


class OkdataError(Exception):
    """An error answer from okdata, or a failure to reach it. Never contains the API key."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        billed: bool | None = False,
        request_id: str | None = None,
        problems: tuple[str, ...] = (),
        next_step: str | None = None,
        retry: str | None = None,
        retry_after_seconds: float | None = None,
        docs_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.billed = billed
        self.request_id = request_id
        self.problems = problems
        self.next_step = next_step
        self.retry = retry
        self.retry_after_seconds = retry_after_seconds
        self.docs_url = docs_url

    def __str__(self) -> str:
        head = f"okdata error {self.code}"
        if self.status:
            head += f" (HTTP {self.status})"
        parts = [f"{head}: {self.message.rstrip('.')}."]
        if self.problems:
            parts.append("Problems: " + "; ".join(self.problems))
        if self.next_step:
            parts.append(self.next_step)
        parts.append(_billed_sentence(self.billed))
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}.")
        if self.docs_url:
            parts.append(f"Docs: {self.docs_url}")
        return " ".join(parts)

    @classmethod
    def from_body(cls, status: int, body: Mapping[str, Any]) -> OkdataError:
        problems = body.get("problems") or ()
        return cls(
            str(body.get("code") or "error"),
            str(body.get("message") or "The request failed"),
            status=status,
            # okdata's own field for whether this call was billed; unknown when a proxy answered instead.
            billed=body.get("charged") if "charged" in body else None,
            request_id=body.get("request_id"),
            problems=tuple(str(p) for p in problems) if isinstance(problems, list) else (),
            next_step=body.get("next_step"),
            retry=body.get("retry"),
            retry_after_seconds=_float_or_none(body.get("retry_after_seconds")),
            docs_url=body.get("docs_url"),
        )


def _billed_sentence(billed: bool | None) -> str:
    if billed is False:
        return "Nothing was billed."
    if billed is True:
        return "This call was billed."
    return "Whether this call was billed is not known yet; look it up by request ID in the okdata console."


def _float_or_none(value: Any) -> float | None:
    try:
        number = None if value is None else float(value)
    except (TypeError, ValueError):
        return None
    return number if number is not None and math.isfinite(number) and number >= 0 else None


def normalize_api_key(raw: Any) -> str:
    """Returns the key without stray whitespace or a pasted `Bearer ` prefix, or raises."""
    key = str(raw or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if not key:
        raise OkdataError("missing_key", f"No okdata API key is set. Create one at {SIGNUP_URL}")
    if not key.startswith(KEY_PREFIX) or any(ch.isspace() for ch in key):
        raise OkdataError(
            "malformed_key",
            f"okdata API keys start with {KEY_PREFIX} and contain no spaces. Copy the key again from the okdata console",
        )
    return key


def api_key_from(credentials: Mapping[str, Any]) -> str:
    return normalize_api_key(credentials.get(CREDENTIAL_NAME))


def normalize_max_price(value: Any) -> str | None:
    """A price cap in US dollars as a plain decimal string, or None for no cap."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        amount = Decimal(str(value).strip().lstrip("$"))
    except InvalidOperation as err:
        raise OkdataError("invalid_max_price", f"max_price must be a number of US dollars, got {value!r}") from err
    if not amount.is_finite() or amount <= 0 or amount > MAX_PRICE_CEILING:
        raise OkdataError(
            "invalid_max_price",
            f"max_price must be above 0 and at most {MAX_PRICE_CEILING} US dollars, got {value!r}",
        )
    text = format(amount.normalize(), "f")
    return text


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_query_value(v) for v in value)
    return str(value)


def clean_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Drops empty values, so an unset optional tool input is never sent."""
    return {
        name: value
        for name, value in (params or {}).items()
        if value is not None and not (isinstance(value, str) and not value.strip())
    }


def http_client() -> httpx.Client:
    """One client per request; tests replace this factory with a mock transport."""
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_SECONDS, follow_redirects=False)


def _headers(api_key: str | None, max_price: str | None, idempotency_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT, "X-Source": SOURCE_LABEL}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if max_price:
        headers["X-Max-Price"] = max_price
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _send_once(
    method: str,
    path: str,
    headers: Mapping[str, str],
    params: Mapping[str, Any],
    body: Mapping[str, Any] | None,
) -> dict[str, Any]:
    with http_client() as http:
        if method == "GET":
            response = http.get(path, headers=dict(headers), params={k: _query_value(v) for k, v in params.items()})
        else:
            response = http.request(method, path, headers=dict(headers), json=dict(body or {}))
    try:
        payload = response.json()
    except ValueError as err:
        raise OkdataError(
            "bad_response",
            "okdata answered with something that is not JSON",
            status=response.status_code,
            billed=None,
        ) from err
    if not isinstance(payload, dict):
        raise OkdataError(
            "bad_response", "okdata answered with an unexpected shape", status=response.status_code, billed=None
        )
    if response.is_success and payload.get("code") == "ok":
        return payload
    raise OkdataError.from_body(response.status_code, payload)


def request(
    method: str,
    path: str,
    *,
    api_key: str | None = None,
    params: Mapping[str, Any] | None = None,
    body: Mapping[str, Any] | None = None,
    max_price: str | None = None,
    idempotent: bool = True,
) -> dict[str, Any]:
    """Sends one call (plus at most one retry) and returns the success envelope, or raises OkdataError.

    Only relative /v1/ paths on api.okdata.online and GET or POST are accepted, so the key can
    never be sent anywhere else.
    """
    method = method.upper()
    if method not in METHODS or not API_PATH.match(path) or ".." in path:
        raise OkdataError("invalid_request", f"Refused to send {method} {path!r}: not an okdata API path")
    paid = bool(api_key) and idempotent
    idempotency_key = str(uuid.uuid4()) if paid else None
    headers = _headers(api_key, max_price, idempotency_key)
    query = clean_params(params)
    for attempt in (1, 2):
        try:
            return _send_once(method, path, headers, query, body)
        except (httpx.ConnectError, httpx.ConnectTimeout) as err:
            # The request never reached okdata, so nothing was billed and a retry is safe.
            if attempt == 2:
                raise OkdataError(
                    "connection_error", f"Could not connect to api.okdata.online ({type(err).__name__})"
                ) from err
            time.sleep(DEFAULT_RETRY_WAIT_SECONDS)
        except (httpx.HTTPError, httpx.InvalidURL) as err:
            # The request may have reached okdata; no second wait inside Dify's own time limit.
            raise OkdataError(
                "client_timeout" if isinstance(err, httpx.TimeoutException) else "connection_error",
                f"The answer from api.okdata.online did not arrive ({type(err).__name__})",
                billed=None if paid else False,
                next_step="The call may still finish. Check Calls in the okdata console before running it again"
                if paid
                else None,
            ) from err
        except OkdataError as err:
            wait = err.retry_after_seconds if err.retry_after_seconds is not None else DEFAULT_RETRY_WAIT_SECONDS
            if attempt == 2 or err.retry not in RETRYABLE or wait > MAX_RETRY_WAIT_SECONDS:
                raise
            time.sleep(wait)
    raise AssertionError("unreachable")


def endpoint_path(endpoint_id: str) -> str:
    if not ENDPOINT_ID.match(endpoint_id):
        raise OkdataError("unknown_endpoint", f"{endpoint_id!r} is not an okdata endpoint id")
    return "/v1/" + endpoint_id.replace(".", "/")


def check_key(api_key: str) -> None:
    """Raises OkdataError unless okdata accepts the key. GET /v1/account is free."""
    request("GET", "/v1/account", api_key=api_key, idempotent=False)
