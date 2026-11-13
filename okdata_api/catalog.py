"""The okdata endpoint catalog (free, no key) and a plain-words search over it.

The search mirrors the one behind okdata's MCP `find` tool: Latin words match whole words
(or substrings from three letters up), Chinese text matches by character pairs, and a few
everyday words map to platform ids ("rednote" -> xiaohongshu, "tweets" -> x).
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from okdata_api import client

CATALOG_PATH = "/v1/catalog"
CACHE_SECONDS = 600.0
SITE_URL = "https://okdata.online"

ALIASES: Mapping[str, tuple[str, ...]] = {
    "twitter": ("x",),
    "tweet": ("x", "post"),
    "tweets": ("x", "post"),
    "推特": ("x",),
    "rednote": ("xiaohongshu",),
    "xhs": ("xiaohongshu",),
    "红书": ("xiaohongshu",),
    "小红书": ("xiaohongshu",),
    "wechat": ("wechat_mp",),
    "weixin": ("wechat_mp",),
    "微信": ("wechat_mp",),
    "公众号": ("wechat_mp",),
    "b站": ("bilibili",),
    "哔哩哔哩": ("bilibili",),
    "yt": ("youtube",),
    "油管": ("youtube",),
    "trending": ("trend",),
    "hot": ("trend",),
    "热搜": ("trend",),
    "热榜": ("trend",),
    "热门": ("trend",),
    "subtitles": ("transcript",),
    "captions": ("transcript",),
    "字幕": ("transcript",),
    "profile": ("account",),
    "user": ("account",),
    "creator": ("account",),
    "用户": ("账号",),
    "博主": ("账号",),
    "粉丝": ("账号",),
    "reviews": ("comments",),
    "口碑": ("评论",),
}

CJK = re.compile(r"[㐀-鿿]")
SPLIT = re.compile(r"[\s,.;:!?()\[\]{}\"'“”‘’，。、；：！？（）《》·_/\-]+")

_cache: dict[str, Any] = {}


def fetch_catalog() -> dict[str, Any]:
    """The live catalog (`data` of GET /v1/catalog), kept in memory for ten minutes."""
    now = time.monotonic()
    cached = _cache.get("catalog")
    if cached is not None and now - _cache.get("at", 0.0) < CACHE_SECONDS:
        return cached
    data = client.request("GET", CATALOG_PATH).get("data") or {}
    if not isinstance(data.get("endpoints"), list):
        raise client.OkdataError("bad_response", "The okdata catalog came back without endpoints")
    _cache.update({"catalog": data, "at": now})
    return data


def clear_cache() -> None:
    _cache.clear()


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _bigrams(run: str) -> list[str]:
    if len(run) <= 2:
        return [run]
    return [run[i : i + 2] for i in range(len(run) - 1)]


def terms_of(query: str) -> list[str]:
    raw = [w for w in SPLIT.split(query.lower()) if w]
    expanded = [t for w in raw for t in (w, *ALIASES.get(w, ()))]
    terms: list[str] = []
    for word in expanded:
        if not CJK.search(word):
            terms.append(_stem(word))
            continue
        alias_hits = [
            _stem(v) for k, vs in ALIASES.items() if CJK.search(k) and k in word and k != word for v in vs
        ]
        terms.extend([*_bigrams(word), *alias_hits])
    return list(dict.fromkeys(terms))


def _platform_names(catalog: Mapping[str, Any]) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for platform in catalog.get("platforms") or []:
        name = platform.get("name") or {}
        names[platform.get("id", "")] = [name.get("en", ""), name.get("zh", "")]
    return names


def _doc(endpoint: Mapping[str, Any], platform_names: Mapping[str, list[str]]) -> dict[str, Any]:
    title = endpoint.get("title") or {}
    summary = endpoint.get("summary") or {}
    aliases = endpoint.get("aliases") or {}
    title_text = " ".join(
        [
            title.get("en", ""),
            title.get("zh", ""),
            *platform_names.get(endpoint.get("platform", ""), []),
            *aliases.get("en", []),
            *aliases.get("zh", []),
        ]
    ).lower()
    text = " ".join(
        [
            endpoint.get("id", "").replace(".", " "),
            endpoint.get("platform", ""),
            endpoint.get("object", ""),
            summary.get("en", ""),
            summary.get("zh", ""),
            " ".join(endpoint.get("jobs") or []).replace("-", " "),
            title_text,
        ]
    ).lower()
    words = {_stem(w) for w in SPLIT.split(text) if w}
    return {"endpoint": endpoint, "title": title_text, "text": text, "words": words}


def _score_term(doc: Mapping[str, Any], term: str) -> int:
    platform = doc["endpoint"].get("platform")
    exact = term in doc["words"] or platform == term
    partial = not exact and (bool(CJK.search(term)) or len(term) >= 3) and term in doc["text"]
    if not exact and not partial:
        return 0
    in_title = term in doc["title"] or platform == term
    return (2 if exact else 1) + (2 if in_title else 0)


def find_endpoints(
    catalog: Mapping[str, Any], query: str, *, platform: str | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    """Endpoints that best match plain words, best first."""
    terms = terms_of(query)
    endpoints: Sequence[Mapping[str, Any]] = catalog.get("endpoints") or []
    if platform:
        endpoints = [e for e in endpoints if e.get("platform") == platform]
    if not terms:
        return [dict(e) for e in endpoints[:limit]] if platform else []
    names = _platform_names(catalog)
    scored = []
    for endpoint in endpoints:
        doc = _doc(endpoint, names)
        score = sum(_score_term(doc, t) for t in terms)
        if score > 0:
            scored.append((score, endpoint))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(e) for _, e in scored[:limit]]


def get_endpoint(catalog: Mapping[str, Any], endpoint_id: str) -> dict[str, Any] | None:
    for endpoint in catalog.get("endpoints") or []:
        if endpoint.get("id") == endpoint_id:
            return dict(endpoint)
    return None


def normalize_endpoint_id(value: str) -> str:
    """Accepts `douyin.videos.search`, `/v1/douyin/videos/search` or a full API URL."""
    text = value.strip()
    text = re.sub(r"^https?://[^/]+", "", text)
    text = re.sub(r"^/?v1/", "", text).strip("/")
    text = text.split("?", 1)[0]
    return text.replace("/", ".")


def docs_url(endpoint_id: str, lang: str = "en") -> str:
    prefix = "/zh" if lang == "zh" else ""
    return f"{SITE_URL}{prefix}/apis/{endpoint_id.replace('.', '/')}/?src=dify-plugin"


def describe(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    """The parts of a catalog entry an agent or a workflow needs to make the call."""
    hidden = {"view", "fields"}
    params = [
        {
            key: value
            for key, value in {
                "name": p.get("name"),
                "type": p.get("type"),
                "required": bool(p.get("required")),
                "enum": p.get("enum"),
                "default": p.get("default"),
                "example": p.get("example"),
                "description": (p.get("description") or {}).get("en"),
            }.items()
            if value is not None
        }
        for p in endpoint.get("params") or []
        if p.get("name") not in hidden
    ]
    title = endpoint.get("title") or {}
    summary = endpoint.get("summary") or {}
    endpoint_id = str(endpoint.get("id", ""))
    return {
        "id": endpoint_id,
        "title": title.get("en"),
        "title_zh": title.get("zh"),
        "summary": summary.get("en"),
        "summary_zh": summary.get("zh"),
        "platform": endpoint.get("platform"),
        "method": endpoint.get("method"),
        "path": endpoint.get("path"),
        "price_usd": endpoint.get("price"),
        "unit": endpoint.get("unit"),
        "max_charge_usd": endpoint.get("maxCharge"),
        "list": bool(endpoint.get("list")),
        "page_size": endpoint.get("pageSize"),
        "status": endpoint.get("status"),
        "paused": bool(endpoint.get("paused")),
        "params": params,
        "docs": docs_url(endpoint_id),
    }
