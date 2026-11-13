"""Runs one okdata endpoint for a Dify tool and turns the answer into tool messages.

Every curated tool is a thin class that calls `run(self, SPECS[...], tool_parameters)`.
A spec names the endpoint, the tool inputs passed through as API parameters, and an
optional clean-up per input (a pasted link turned into the ID the endpoint wants).
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


@dataclass(frozen=True)
class EndpointSpec:
    """One curated tool. `max_price` is the cap used when the tool's Max price setting is empty;
    it matches the default in the tool's YAML (a test keeps them in sync)."""

    endpoint_id: str
    title: str
    max_price: str
    params: tuple[str, ...] = ()
    clean: Mapping[str, Callable[[str], str]] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return client.endpoint_path(self.endpoint_id)


SPECS: Mapping[str, EndpointSpec] = {
    "tiktok_search_videos": EndpointSpec("tiktok.videos.search", "TikTok video search", "0.01", ("query", "sort", "cursor")),
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


def api_params(spec: EndpointSpec, tool_parameters: Mapping[str, Any]) -> dict[str, Any]:
    """The API parameters for this call: the spec's inputs that are set, cleaned up."""
    chosen = client.clean_params({name: tool_parameters.get(name) for name in spec.params})
    return {name: spec.clean[name](str(value)) if name in spec.clean else value for name, value in chosen.items()}


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
