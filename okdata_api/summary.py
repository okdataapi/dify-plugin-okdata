"""Readable text and workflow variables from an okdata success envelope.

The text is what a person or an LLM reads in the tool output: one line per item with the
fields that matter (title or text, author, counts, link), then what the call cost and how
to get the next page. The full envelope always goes out as JSON next to it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_LINES = 30
MAX_SNIPPET = 140
MAX_LONG_TEXT = 20000
METRIC_LABELS = (
    ("views", "views"),
    ("likes", "likes"),
    ("comments", "comments"),
    ("shares", "shares"),
    ("favorites", "saves"),
    ("reposts", "reposts"),
)


def _compact_number(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    for size, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if abs(value) >= size:
            return f"{value / size:.1f}".rstrip("0").rstrip(".") + suffix
    return f"{value:g}"


def _snippet(text: Any, limit: int = MAX_SNIPPET) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _metrics_text(metrics: Any) -> str:
    if not isinstance(metrics, Mapping):
        return ""
    parts = [f"{_compact_number(metrics[k])} {label}" for k, label in METRIC_LABELS if metrics.get(k) is not None]
    return ", ".join(parts)


def _author_name(item: Mapping[str, Any]) -> str:
    author = item.get("author")
    if not isinstance(author, Mapping):
        return ""
    return str(author.get("name") or author.get("username") or "")


def _describe_item(item: Any) -> str:
    if not isinstance(item, Mapping):
        return _snippet(item)
    if "rank" in item and "name" in item:
        heat = f" (heat {_compact_number(item['heat'])})" if item.get("heat") is not None else ""
        url = f"\n   {item['url']}" if item.get("url") else ""
        return f"{_snippet(item['name'])}{heat}{url}"
    head = item.get("title") or item.get("text") or item.get("name") or item.get("id") or ""
    details = [d for d in (_author_name(item), _metrics_text(item.get("metrics"))) if d]
    if item.get("likes") is not None and "metrics" not in item:
        details.append(f"{_compact_number(item['likes'])} likes")
    if item.get("replies") is not None:
        details.append(f"{_compact_number(item['replies'])} replies")
    if item.get("published_at"):
        details.append(str(item["published_at"])[:10])
    line = _snippet(head)
    if details:
        line += " | " + " | ".join(details)
    if item.get("url"):
        line += f"\n   {item['url']}"
    return line


def _item_line(index: int, item: Any) -> str:
    if isinstance(item, Mapping) and "rank" in item and "name" in item:
        return f"{item['rank']}. {_describe_item(item)}"
    return f"{index}. {_describe_item(item)}"


def _cost_line(envelope: Mapping[str, Any]) -> str:
    billing = (envelope.get("meta") or {}).get("billing") or {}
    parts = []
    if billing.get("amount") is not None:
        parts.append(f"Cost: ${billing['amount']}")
    if billing.get("balance_after") is not None:
        parts.append(f"balance left: ${billing['balance_after']}")
    if billing.get("covers_next") is False:
        parts.append("the balance will not cover another call like this one")
    return ", ".join(parts) + "." if parts else ""


def _single_item_text(item: Mapping[str, Any]) -> list[str]:
    if isinstance(item.get("segments"), list) or ("text" in item and "video_id" in item):
        text = str(item.get("text") or " ".join(s.get("text", "") for s in item.get("segments") or []))
        lines = [f"Transcript, language {item.get('lang') or 'unknown'}, {len(item.get('segments') or [])} segments:"]
        lines.append(text if len(text) <= MAX_LONG_TEXT else text[:MAX_LONG_TEXT] + " … (truncated; full text in JSON)")
        return lines
    lines = [_describe_item(item)]
    metrics = item.get("metrics")
    if isinstance(metrics, Mapping) and _metrics_text(metrics):
        lines.append("Counts: " + _metrics_text(metrics))
    ext = item.get("ext")
    if isinstance(ext, Mapping):
        extras = {k: v for k, v in ext.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if extras:
            lines.append("More: " + ", ".join(f"{k} {_compact_number(v)}" for k, v in extras.items()))
    body = item.get("text")
    if isinstance(body, str) and len(body) > MAX_SNIPPET:
        lines.append(body if len(body) <= MAX_LONG_TEXT else body[:MAX_LONG_TEXT] + " … (truncated; full text in JSON)")
    return lines


def summarize(title: str, envelope: Mapping[str, Any]) -> str:
    data = envelope.get("data") or {}
    page = envelope.get("page") or {}
    meta = envelope.get("meta") or {}
    lines: list[str] = []
    items = data.get("items") if isinstance(data, Mapping) else None
    if isinstance(items, list):
        lines.append(f"{title}: {len(items)} result{'s' if len(items) != 1 else ''}.")
        lines.extend(_item_line(i, item) for i, item in enumerate(items[:MAX_LINES], start=1))
        if len(items) > MAX_LINES:
            lines.append(f"… and {len(items) - MAX_LINES} more in the JSON output.")
        missing = data.get("missing")
        if missing:
            lines.append(f"Not found: {', '.join(str(m) for m in missing)}.")
    elif isinstance(data, Mapping) and isinstance(data.get("item"), Mapping):
        lines.append(f"{title}:")
        lines.extend(_single_item_text(data["item"]))
    else:
        lines.append(f"{title}: done.")
    if meta.get("result_status") == "empty":
        lines.append("The platform returned nothing for this request.")
    for warning in envelope.get("warnings") or []:
        lines.append(f"Note: {warning if isinstance(warning, str) else warning.get('message', warning)}")
    cost = _cost_line(envelope)
    if cost:
        lines.append(cost)
    if page.get("has_more") and page.get("next_cursor"):
        lines.append(f"More results: call again with cursor = {page['next_cursor']} (each page is a separate call).")
    return "\n".join(lines)


def variables(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Named outputs a workflow can reference without parsing JSON."""
    data = envelope.get("data") or {}
    page = envelope.get("page") or {}
    billing = ((envelope.get("meta") or {}).get("billing")) or {}
    out: dict[str, Any] = {
        "cost": "" if billing.get("amount") is None else str(billing["amount"]),
        "balance_after": "" if billing.get("balance_after") is None else str(billing["balance_after"]),
        "request_id": str(envelope.get("request_id") or ""),
        "result_status": str((envelope.get("meta") or {}).get("result_status") or ""),
    }
    if isinstance(data, Mapping) and isinstance(data.get("items"), list):
        out["items"] = data["items"]
        out["next_cursor"] = str(page.get("next_cursor") or "")
        out["has_more"] = bool(page.get("has_more"))
    elif isinstance(data, Mapping) and "item" in data:
        out["item"] = data.get("item") or {}
    return out
