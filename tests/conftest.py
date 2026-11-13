"""Test helpers: a mock okdata API (httpx.MockTransport) and real tool instances."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from okdata_api import catalog, client  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
TEST_KEY = "okd_test_0123456789abcdef"


def ok_envelope(data: dict[str, Any], *, page: dict[str, Any] | None = None, amount: str = "0.002") -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": "ok",
        "request_id": "0f6c2a8e-4b1d-4e0a-9a51-3c7d2b9e1f20",
        "data": data,
        "warnings": [],
        "meta": {
            "result_status": "complete",
            "billing": {"amount": amount, "currency": "USD", "balance_after": "4.998"},
        },
    }
    if page is not None:
        body["page"] = page
    return body


def error_body(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "code": code,
        "request_id": "a5b48f50-c209-4cad-a455-19421ec36ee5",
        "message": message,
        "charged": False,
        "retry": "no",
        "retry_after_seconds": None,
        "problems": [],
        "docs_url": f"https://okdata.online/docs/errors/#{code}",
        **extra,
    }


class MockApi:
    """Records requests and answers them with a handler (request -> (status, json body))."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.handler: Callable[[httpx.Request], tuple[int, Any]] = lambda request: (404, {"code": "not_found"})

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.handler(request)
        if isinstance(body, (bytes, str)):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def catalog_body() -> dict[str, Any]:
    return json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> MockApi:
    mock = MockApi()

    def factory() -> httpx.Client:
        return httpx.Client(base_url=client.BASE_URL, transport=httpx.MockTransport(mock))

    monkeypatch.setattr(client, "http_client", factory)
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)
    catalog.clear_cache()
    yield mock
    catalog.clear_cache()


def collect(messages: Any) -> dict[str, Any]:
    """Splits tool messages into text, json and variables."""
    out: dict[str, Any] = {"text": [], "json": [], "variables": {}}
    for message in messages:
        kind = message.type.value if hasattr(message.type, "value") else str(message.type)
        payload = message.message
        if kind == "text":
            out["text"].append(payload.text)
        elif kind == "json":
            out["json"].append(payload.json_object)
        elif kind == "variable":
            out["variables"][payload.variable_name] = payload.variable_value
    return out
