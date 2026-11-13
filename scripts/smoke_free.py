"""Live smoke test against https://api.okdata.online using FREE routes only.

    .venv/bin/python scripts/smoke_free.py

1. The Find tool against the live catalog (no key, nothing billed).
2. Credential check with a made-up key: must fail cleanly with `unauthorized`.
3. Every curated tool's endpoint still exists, takes the tool's inputs, and its
   most expensive call fits under the tool's default price cap.

It never sends a real key and never calls a data endpoint.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dify_plugin.errors.tool import ToolProviderCredentialValidationError  # noqa: E402

from okdata_api import catalog, runner  # noqa: E402
from provider.okdata import OkdataProvider  # noqa: E402
from tools.find_endpoint import FindEndpointTool  # noqa: E402

FAKE_KEY = "okd_smoke_test_not_a_real_key"


def check_find() -> None:
    tool = FindEndpointTool.from_credentials({"okdata_api_key": FAKE_KEY})
    messages = list(tool.invoke({"query": "抖音 评论", "limit": 3}))
    found = next(m.message.variable_value for m in messages if getattr(m.message, "variable_name", "") == "endpoints")
    ids = [e["id"] for e in found]
    assert "douyin.videos.comments.list" in ids, ids
    print(f"ok  find_endpoint('抖音 评论') -> {ids}")


def check_bad_key() -> None:
    try:
        OkdataProvider().validate_credentials({"okdata_api_key": FAKE_KEY})
    except ToolProviderCredentialValidationError as err:
        text = str(err)
        assert "unauthorized" in text and FAKE_KEY not in text, text
        print(f"ok  bad key refused: {text[:110]}...")
        return
    raise AssertionError("a made-up key was accepted")


def check_specs() -> None:
    data = catalog.fetch_catalog()
    for name, spec in runner.SPECS.items():
        endpoint = catalog.get_endpoint(data, spec.endpoint_id)
        assert endpoint is not None, f"{name}: {spec.endpoint_id} is not in the live catalog"
        api_params = {p["name"] for p in endpoint["params"]}
        assert set(spec.params) <= api_params, f"{name}: {set(spec.params) - api_params} not accepted"
        assert Decimal(endpoint["maxCharge"]) <= Decimal(spec.max_price), f"{name}: max charge above default cap"
        print(f"ok  {name:28} {spec.endpoint_id:36} ${endpoint['price']}/{endpoint['unit']} (cap ${spec.max_price})")


if __name__ == "__main__":
    check_find()
    check_bad_key()
    check_specs()
    print("live smoke test passed (free routes only)")
