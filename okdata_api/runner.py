"""Runs one okdata endpoint for a Dify tool and turns the answer into tool messages.

Every curated tool is a thin class that calls `run(self, SPECS[...], tool_parameters)`.
A spec names the endpoint, the tool inputs passed through as API parameters, an
optional clean-up per input (a pasted link turned into the ID the endpoint wants), and,
for endpoints that take either an ID or a link, the API parameter a link is sent as when
no ID could be read from it (a Reddit share link, say).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Generator, Mapping
from dataclasses import dataclass, field
from typing import Any

from okdata_api import client, summary

YOUTUBE_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")
DOUYIN_ID = re.compile(r"(?:/video/|/note/|modal_id=|aweme_id=)(\d{15,21})")
XHS_NOTE_ID = re.compile(r"(?:/explore/|/discovery/item/|/item/)([0-9a-f]{24})")
TIKTOK_ID = re.compile(r"/(?:video|photo)/(\d{15,21})")
INSTAGRAM_SHORTCODE = re.compile(r"(?:instagram\.com|instagr\.am)/(?:[A-Za-z0-9._]+/)?(?:p|reels?|tv)/([A-Za-z0-9_-]+)")
INSTAGRAM_HANDLE = re.compile(r"instagram\.com/(?!(?:p|reels?|tv|stories|explore)/)([A-Za-z0-9._]+)")
REDDIT_POST_ID = re.compile(r"(?:/comments/|redd\.it/)([A-Za-z0-9]+)")
AMAZON_ASIN = re.compile(r"/(?:dp|gp/product|gp/aw/d|product-reviews)/([A-Za-z0-9]{10})(?![A-Za-z0-9])")
LINK = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|www\.|[a-z0-9-]+(?:\.[a-z0-9-]+)+/)", re.IGNORECASE)


def youtube_video_id(value: str) -> str:
    """`dQw4w9WgXcQ`, or the ID inside a watch, youtu.be, shorts, embed or live link."""
    text = value.strip()
    match = YOUTUBE_ID.search(text)
    return match.group(1) if match else text


def douyin_video_id(value: str) -> str:
    """The numeric video ID, also from a douyin.com/video/... link. Short v.douyin.com links are passed as-is."""
    text = value.strip()
    match = DOUYIN_ID.search(text)
    return match.group(1) if match else text


def xiaohongshu_note_id(value: str) -> str:
    """The 24-character note ID, also from a xiaohongshu.com/explore/... link."""
    text = value.strip()
    match = XHS_NOTE_ID.search(text)
    return match.group(1) if match else text


def tiktok_video_id(value: str) -> str:
    """The numeric video ID, also from a tiktok.com/@user/video/... link. Short links are passed as-is."""
    text = value.strip()
    match = TIKTOK_ID.search(text)
    return match.group(1) if match else text


def instagram_handle(value: str) -> str:
    """The handle, also from an instagram.com/<handle> profile link. A leading @ is kept; okdata accepts it."""
    text = value.strip()
    match = INSTAGRAM_HANDLE.search(text)
    return match.group(1) if match else text


def instagram_shortcode(value: str) -> str:
    """The post shortcode from an instagram.com/p/..., /reel/... or /tv/... link; anything else as-is."""
    text = value.strip()
    match = INSTAGRAM_SHORTCODE.search(text)
    return match.group(1) if match else text


def reddit_post_id(value: str) -> str:
    """The post ID from a reddit.com/r/.../comments/<id>/ or redd.it/<id> link; anything else as-is."""
    text = value.strip()
    match = REDDIT_POST_ID.search(text)
    return match.group(1) if match else text


def amazon_asin(value: str) -> str:
    """The 10-character ASIN, also from an Amazon product link (/dp/, /gp/product/, /product-reviews/)."""
    text = value.strip()
    match = AMAZON_ASIN.search(text)
    return match.group(1).upper() if match else text


def is_link(value: Any) -> bool:
    return isinstance(value, str) and bool(LINK.match(value.strip()))


@dataclass(frozen=True)
class EndpointSpec:
    """One curated tool. `max_price` is the cap used when the tool's Max price setting is empty;
    it matches the default in the tool's YAML (a test keeps them in sync)."""

    endpoint_id: str
    title: str
    max_price: str
    params: tuple[str, ...] = ()
    clean: Mapping[str, Callable[[str], str]] = field(default_factory=dict)
    # input -> API parameter to send it as when, after clean-up, it is still a link
    links: Mapping[str, str] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return client.endpoint_path(self.endpoint_id)


SPECS: Mapping[str, EndpointSpec] = {
    "tiktok_search_videos": EndpointSpec("tiktok.videos.search", "TikTok video search", "0.01", ("query", "sort", "cursor")),
    "tiktok_video_comments": EndpointSpec(
        "tiktok.videos.comments.list", "TikTok video comments", "0.01", ("id", "cursor"), {"id": tiktok_video_id}
    ),
    "youtube_search_videos": EndpointSpec("youtube.videos.search", "YouTube video search", "0.01", ("query", "sort", "cursor")),
    "youtube_video_comments": EndpointSpec(
        "youtube.videos.comments.list", "YouTube video comments", "0.01", ("id", "sort", "cursor"), {"id": youtube_video_id}
    ),
    "instagram_profile": EndpointSpec(
        "instagram.users.get", "Instagram profile", "0.01", ("username",), {"username": instagram_handle}
    ),
    "instagram_account_posts": EndpointSpec(
        "instagram.users.posts.list",
        "Instagram account posts",
        "0.01",
        ("username", "type", "cursor"),
        {"username": instagram_handle},
    ),
    "instagram_post_comments": EndpointSpec(
        "instagram.posts.comments.list",
        "Instagram post comments",
        "0.01",
        ("id", "cursor"),
        {"id": instagram_shortcode},
        {"id": "url"},
    ),
    "x_trending_topics": EndpointSpec("x.trends.list", "X trending topics", "0.02", ("country", "cursor")),
    "reddit_search_posts": EndpointSpec(
        "reddit.posts.search", "Reddit post search", "0.01", ("query", "sort", "published_within", "cursor")
    ),
    "reddit_post_comments": EndpointSpec(
        "reddit.posts.comments.list",
        "Reddit post comments",
        "0.01",
        ("id", "sort", "cursor"),
        {"id": reddit_post_id},
        {"id": "url"},
    ),
    "amazon_search_products": EndpointSpec(
        "amazon.products.search", "Amazon product search", "0.02", ("query", "country", "sort", "cursor")
    ),
    "amazon_product_reviews": EndpointSpec(
        "amazon.products.reviews.list", "Amazon product reviews", "0.02", ("id", "country"), {"id": amazon_asin}
    ),
    "xiaohongshu_search_notes": EndpointSpec(
        "xiaohongshu.notes.search", "RedNote (Xiaohongshu) note search", "0.05", ("query", "sort", "type", "cursor")
    ),
    "xiaohongshu_note_comments": EndpointSpec(
        "xiaohongshu.notes.comments.list",
        "RedNote (Xiaohongshu) note comments",
        "0.05",
        ("id", "cursor"),
        {"id": xiaohongshu_note_id},
    ),
    "douyin_search_videos": EndpointSpec("douyin.videos.search", "Douyin video search", "0.05", ("query", "sort", "cursor")),
    "douyin_video_comments": EndpointSpec(
        "douyin.videos.comments.list", "Douyin video comments", "0.01", ("id", "cursor"), {"id": douyin_video_id}
    ),
    "douyin_hot_search": EndpointSpec("douyin.trends.list", "Douyin hot search", "0.01"),
    "weibo_hot_search": EndpointSpec("weibo.trends.list", "Weibo hot search", "0.01"),
    "wechat_search_articles": EndpointSpec(
        "wechat.posts.search", "WeChat Search", "0.05", ("query", "sort", "published_within", "type", "cursor")
    ),
    "wechat_account_articles": EndpointSpec(
        "wechat_mp.accounts.articles.list", "WeChat Official Account articles", "0.05", ("id", "tab", "cursor")
    ),
    "wechat_article_stats": EndpointSpec("wechat_mp.articles.metrics", "WeChat article reads and likes", "0.05", ("url",)),
    "x_search_posts": EndpointSpec("x.posts.search", "X post search", "0.01", ("query", "sort", "cursor")),
    "youtube_transcript": EndpointSpec(
        "youtube.videos.transcript.get", "YouTube transcript", "0.01", ("id", "lang"), {"id": youtube_video_id}
    ),
}


def _api_name(spec: EndpointSpec, name: str, value: Any) -> str:
    return spec.links[name] if name in spec.links and is_link(value) else name


def api_params(spec: EndpointSpec, tool_parameters: Mapping[str, Any]) -> dict[str, Any]:
    """The API parameters for this call: the spec's inputs that are set, cleaned up, and a link
    that still is one after clean-up sent under the endpoint's link parameter."""
    chosen = client.clean_params({name: tool_parameters.get(name) for name in spec.params})
    cleaned = {name: spec.clean[name](str(value)) if name in spec.clean else value for name, value in chosen.items()}
    return {_api_name(spec, name, value): value for name, value in cleaned.items()}


def messages(tool: Any, title: str, envelope: Mapping[str, Any]) -> Generator[Any, None, None]:
    """Text for people and LLMs, the JSON envelope, and named variables for workflows."""
    yield tool.create_text_message(summary.summarize(title, envelope))
    yield tool.create_json_message(dict(envelope))
    for name, value in summary.variables(envelope).items():
        yield tool.create_variable_message(name, value)


def run(tool: Any, spec: EndpointSpec, tool_parameters: Mapping[str, Any]) -> Generator[Any, None, None]:
    api_key = client.api_key_from(tool.runtime.credentials)
    max_price = client.normalize_max_price(tool_parameters.get("max_price")) or spec.max_price
    envelope = client.request(
        "GET", spec.path, api_key=api_key, params=api_params(spec, tool_parameters), max_price=max_price
    )
    yield from messages(tool, spec.title, envelope)
