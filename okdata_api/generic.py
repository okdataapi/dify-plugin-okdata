"""The two catalog-wide tools: find an endpoint (free) and call any endpoint by its id."""

from __future__ import annotations

import json
import math
from collections.abc import Generator, Mapping
from typing import Any

from okdata_api import catalog, client, runner

DEFAULT_MAX_PRICE = "0.1"  # matches the max_price default in tools/call_endpoint.yaml
MAX_FIND_RESULTS = 20
DEFAULT_FIND_RESULTS = 5
RESERVED_PARAMS = frozenset({"max_price"})
SCALARS = (str, int, float, bool)
FREE_FORM_PARAMS = frozenset({"cursor", "view", "fields"})


def _refuse_constant(name: str) -> Any:
    raise client.OkdataError("invalid_params", f"params may not contain {name}")


def _is_scalar(value: Any) -> bool:
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return isinstance(value, SCALARS)


def parse_params(raw: Any) -> dict[str, Any]:
    """The `params` input: a JSON object of API parameters (a dict is accepted too)."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return {}
    if isinstance(raw, Mapping):
        parsed: Any = dict(raw)
    else:
        try:
            parsed = json.loads(str(raw), parse_constant=_refuse_constant)
        except json.JSONDecodeError as err:
            raise client.OkdataError(
                "invalid_params",
                f'params must be a JSON object such as {{"query": "coffee"}}; it could not be parsed ({err.msg})',
            ) from err
    if not isinstance(parsed, dict):
        raise client.OkdataError("invalid_params", 'params must be a JSON object such as {"query": "coffee"}')
    for name, value in parsed.items():
        ok = value is None or _is_scalar(value)
        ok = ok or (isinstance(value, list) and all(_is_scalar(v) for v in value))
        if not ok:
            raise client.OkdataError(
                "invalid_params", f"params.{name} must be a string, number, true/false or a list of those"
            )
    return parsed


def _unknown_endpoint(data: Mapping[str, Any], endpoint_id: str) -> client.OkdataError:
    guesses = catalog.find_endpoints(data, endpoint_id.replace(".", " ").replace("_", " "), limit=3)
    hint = f" Did you mean: {', '.join(g['id'] for g in guesses)}?" if guesses else ""
    return client.OkdataError(
        "unknown_endpoint",
        f"No okdata endpoint has the id {endpoint_id!r}.{hint} Use the Find an okdata Endpoint tool (free) to look one up",
    )


def call_endpoint(tool: Any, tool_parameters: Mapping[str, Any]) -> Generator[Any, None, None]:
    api_key = client.api_key_from(tool.runtime.credentials)
    max_price = client.normalize_max_price(tool_parameters.get("max_price")) or DEFAULT_MAX_PRICE
    endpoint_id = catalog.normalize_endpoint_id(str(tool_parameters.get("endpoint_id") or ""))
    if not endpoint_id:
        raise client.OkdataError("invalid_params", "endpoint_id is required, for example douyin.videos.search")
    params = parse_params(tool_parameters.get("params"))
    ignored = sorted(RESERVED_PARAMS & params.keys())
    params = {k: v for k, v in params.items() if k not in RESERVED_PARAMS}
    view = tool_parameters.get("view")
    if view and "view" not in params:
        params = {**params, "view": view}

    data = catalog.fetch_catalog()
    endpoint = catalog.get_endpoint(data, endpoint_id)
    if endpoint is None:
        raise _unknown_endpoint(data, endpoint_id)

    accepted = {str(p.get("name")) for p in endpoint.get("params") or []} | FREE_FORM_PARAMS
    unknown = sorted(set(params) - accepted)
    if unknown:
        raise client.OkdataError(
            "invalid_params",
            f"{endpoint_id} does not take {', '.join(unknown)}. It takes: {', '.join(sorted(accepted))}",
        )

    method = "POST" if str(endpoint.get("method")).upper() == "POST" else "GET"
    path = client.endpoint_path(endpoint_id)  # built from the id, never taken from elsewhere
    if method == "GET":
        envelope = client.request("GET", path, api_key=api_key, params=params, max_price=max_price)
    else:
        envelope = client.request(method, path, api_key=api_key, body=params, max_price=max_price)
    if ignored:
        note = "max_price in params was ignored: the cap is this tool's Max price setting."
        envelope = {**envelope, "warnings": [*(envelope.get("warnings") or []), note]}
    title = (endpoint.get("title") or {}).get("en") or endpoint_id
    yield from runner.messages(tool, f"{title} ({endpoint_id})", envelope)


def _limit(raw: Any) -> int:
    try:
        value = int(float(raw)) if raw not in (None, "") else DEFAULT_FIND_RESULTS
    except (TypeError, ValueError, OverflowError):
        value = DEFAULT_FIND_RESULTS
    return max(1, min(MAX_FIND_RESULTS, value))


def _param_text(param: Mapping[str, Any]) -> str:
    text = str(param.get("name"))
    if param.get("enum"):
        text += " (" + " | ".join(str(v) for v in param["enum"]) + ")"
    return text


def _find_text(query: str, found: list[dict[str, Any]]) -> str:
    if not found:
        return (
            f'No okdata endpoint matched "{query}". Try other words (platform names in English or Chinese work), '
            "or browse https://okdata.online/apis/?src=dify-plugin"
        )
    lines = [f'okdata endpoints for "{query}" (looking up is free):']
    for i, e in enumerate(found, start=1):
        required = [_param_text(p) for p in e["params"] if p.get("required")]
        optional = [_param_text(p) for p in e["params"] if not p.get("required")]
        lines.append(f"{i}. {e['id']}: {e['title']} / {e['title_zh']}. ${e['price_usd']} per {e['unit']}.")
        if e.get("summary"):
            lines.append(f"   {e['summary']}")
        lines.append(f"   Required: {', '.join(required) or 'none'}. Optional: {', '.join(optional) or 'none'}.")
        lines.append(f"   {e['docs']}")
    lines.append("Call one with the Call Any okdata Endpoint tool: endpoint_id plus params as a JSON object.")
    return "\n".join(lines)


def find_endpoint(tool: Any, tool_parameters: Mapping[str, Any]) -> Generator[Any, None, None]:
    query = str(tool_parameters.get("query") or "").strip()
    platform = str(tool_parameters.get("platform") or "").strip() or None
    if not query and not platform:
        raise client.OkdataError("invalid_params", "Give a few words to search for, e.g. 'douyin comments'")
    data = catalog.fetch_catalog()
    found = [catalog.describe(e) for e in catalog.find_endpoints(data, query, platform=platform, limit=_limit(tool_parameters.get("limit")))]
    yield tool.create_text_message(_find_text(query or str(platform), found))
    yield tool.create_json_message({"query": query, "platform": platform, "endpoints": found, "revision": data.get("revision")})
    yield tool.create_variable_message("endpoints", found)
    yield tool.create_variable_message("count", len(found))
