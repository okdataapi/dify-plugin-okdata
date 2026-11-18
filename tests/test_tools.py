from __future__ import annotations

import importlib
from typing import Any

import pytest
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from okdata_api import client, runner
from tests.conftest import TEST_KEY, collect, error_body, ok_envelope

CREDENTIALS = {"okdata_api_key": TEST_KEY}

# tool name -> (inputs, expected path, expected query)
CURATED: dict[str, tuple[dict[str, Any], str, dict[str, str]]] = {
    "tiktok_video_comments": ({"id": "https://www.tiktok.com/@nasa/video/7305085486984858894?lang=en"}, "/v1/tiktok/videos/comments/list", {"id": "7305085486984858894"}),
    "youtube_search_videos": ({"query": "claude code tutorial", "sort": "most_viewed"}, "/v1/youtube/videos/search", {"query": "claude code tutorial", "sort": "most_viewed"}),
    "youtube_video_comments": ({"id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "sort": "latest"}, "/v1/youtube/videos/comments/list", {"id": "dQw4w9WgXcQ", "sort": "latest"}),
    "instagram_profile": ({"username": "https://www.instagram.com/nasa/"}, "/v1/instagram/users/get", {"username": "nasa"}),
    "instagram_account_posts": ({"username": "@nasa", "type": "reel", "cursor": ""}, "/v1/instagram/users/posts/list", {"username": "@nasa", "type": "reel"}),
    "instagram_post_comments": ({"id": "https://www.instagram.com/reel/DeCPVhERA8e/?igsh=abc"}, "/v1/instagram/posts/comments/list", {"id": "DeCPVhERA8e"}),
    "x_trending_topics": ({"country": "US"}, "/v1/x/trends/list", {"country": "US"}),
    "reddit_search_posts": ({"query": "standing desk", "sort": "popular", "published_within": "week"}, "/v1/reddit/posts/search", {"query": "standing desk", "sort": "popular", "published_within": "week"}),
    "reddit_post_comments": ({"id": "https://www.reddit.com/r/nasa/s/AbCdEf123", "sort": "latest"}, "/v1/reddit/posts/comments/list", {"url": "https://www.reddit.com/r/nasa/s/AbCdEf123", "sort": "latest"}),
    "amazon_search_products": ({"query": "portable espresso maker", "country": "DE", "sort": "best_sellers"}, "/v1/amazon/products/search", {"query": "portable espresso maker", "country": "DE", "sort": "best_sellers"}),
    "amazon_product_reviews": ({"id": "https://www.amazon.com/Fanttik-Espresso/dp/B0GTS6KPPB/ref=sr_1_1", "country": "US"}, "/v1/amazon/products/reviews/list", {"id": "B0GTS6KPPB", "country": "US"}),
    "tiktok_search_videos": ({"query": "ai agents", "sort": "latest", "max_price": 0.01}, "/v1/tiktok/videos/search", {"query": "ai agents", "sort": "latest"}),
    "xiaohongshu_search_notes": ({"query": "防晒霜", "sort": "popular", "type": "image", "cursor": ""}, "/v1/xiaohongshu/notes/search", {"query": "防晒霜", "sort": "popular", "type": "image"}),
    "xiaohongshu_note_comments": ({"id": "https://www.xiaohongshu.com/explore/6650a1b2000000001e00abcd?xsec_token=x"}, "/v1/xiaohongshu/notes/comments/list", {"id": "6650a1b2000000001e00abcd"}),
    "douyin_search_videos": ({"query": "露营装备", "cursor": "c1.abc"}, "/v1/douyin/videos/search", {"query": "露营装备", "cursor": "c1.abc"}),
    "douyin_video_comments": ({"id": "https://www.douyin.com/video/7301234567890123456"}, "/v1/douyin/videos/comments/list", {"id": "7301234567890123456"}),
    "douyin_hot_search": ({}, "/v1/douyin/trends/list", {}),
    "weibo_hot_search": ({}, "/v1/weibo/trends/list", {}),
    "wechat_search_articles": ({"query": "咖啡店开业", "published_within": "week", "type": "article"}, "/v1/wechat/posts/search", {"query": "咖啡店开业", "published_within": "week", "type": "article"}),
    "wechat_account_articles": ({"id": "gh_363b924965e9", "tab": "articles"}, "/v1/wechat_mp/accounts/articles/list", {"id": "gh_363b924965e9", "tab": "articles"}),
    "wechat_article_stats": ({"url": "https://mp.weixin.qq.com/s/abc"}, "/v1/wechat_mp/articles/metrics", {"url": "https://mp.weixin.qq.com/s/abc"}),
    "x_search_posts": ({"query": '"claude code" lang:en', "sort": "top"}, "/v1/x/posts/search", {"query": '"claude code" lang:en', "sort": "top"}),
    "youtube_transcript": ({"id": "https://youtu.be/dQw4w9WgXcQ?t=3", "lang": "en"}, "/v1/youtube/videos/transcript/get", {"id": "dQw4w9WgXcQ", "lang": "en"}),
}


def tool_class(name: str):
    module = importlib.import_module(f"tools.{name}")
    classes = [v for v in vars(module).values() if isinstance(v, type) and v.__module__ == module.__name__]
    assert len(classes) == 1
    return classes[0]


def run_tool(name: str, params: dict[str, Any], credentials: dict[str, Any] = CREDENTIALS) -> dict[str, Any]:
    tool = tool_class(name).from_credentials(credentials)
    return collect(tool.invoke(dict(params)))


def test_every_curated_tool_has_a_case():
    assert set(CURATED) == set(runner.SPECS)


@pytest.mark.parametrize("name", sorted(CURATED))
def test_curated_tool_calls_its_endpoint(api, name):
    inputs, path, query = CURATED[name]
    api.handler = lambda request: (200, ok_envelope({"items": [{"id": "1", "text": "hello", "url": "https://example.com/1"}]}, page={"has_more": True, "next_cursor": "c1.next"}))
    out = run_tool(name, inputs)
    sent = api.last
    assert sent.url.path == path
    assert dict(sent.url.params) == query
    assert sent.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert sent.headers["X-Source"] == "dify"
    assert "X-Max-Price" in sent.headers  # every curated tool has a default cap
    assert out["json"][0]["code"] == "ok"
    assert "hello" in out["text"][0]
    assert out["variables"]["items"][0]["id"] == "1"
    assert out["variables"]["next_cursor"] == "c1.next"
    assert out["variables"]["has_more"] is True
    assert out["variables"]["cost"] == "0.002"


def test_max_price_from_the_tool_setting_is_sent(api):
    api.handler = lambda request: (200, ok_envelope({"items": []}))
    run_tool("x_search_posts", {"query": "a", "max_price": 0.005})
    assert api.last.headers["X-Max-Price"] == "0.005"


def test_api_error_becomes_a_readable_exception(api):
    api.handler = lambda request: (400, error_body("max_price_exceeded", "This call could cost more than the price cap allows"))
    with pytest.raises(client.OkdataError) as err:
        run_tool("xiaohongshu_search_notes", {"query": "a", "max_price": 0.001})
    assert "max_price_exceeded" in str(err.value)
    assert "Nothing was billed." in str(err.value)


def test_tool_without_key_fails_before_any_request(api):
    with pytest.raises(client.OkdataError):
        run_tool("weibo_hot_search", {}, credentials={})
    assert api.requests == []


def test_single_item_tool_returns_item_variable(api):
    item = {"id": "a1", "url": "https://mp.weixin.qq.com/s/abc", "type": "article", "title": "Title", "text": "", "metrics": {"views": 12345, "likes": 67}, "ext": {"recommends": 8}}
    api.handler = lambda request: (200, ok_envelope({"item": item}, amount="0.02"))
    out = run_tool("wechat_article_stats", {"url": "https://mp.weixin.qq.com/s/abc"})
    assert out["variables"]["item"]["metrics"]["views"] == 12345
    assert "12.3k views" in out["text"][0]
    assert "recommends 8" in out["text"][0]
    assert "items" not in out["variables"]


class TestProvider:
    def provider(self):
        module = importlib.import_module("provider.okdata")
        return module.OkdataProvider()

    def test_valid_key_passes(self, api):
        api.handler = lambda request: (200, ok_envelope({"balance": "5.00", "currency": "USD"}))
        self.provider().validate_credentials({"okdata_api_key": TEST_KEY})
        assert api.last.url.path == "/v1/account"
        assert api.last.method == "GET"

    def test_refused_key_fails_with_message(self, api):
        api.handler = lambda request: (401, error_body("unauthorized", "No credential was sent, or it is invalid, disabled or expired"))
        with pytest.raises(ToolProviderCredentialValidationError) as err:
            self.provider().validate_credentials({"okdata_api_key": TEST_KEY})
        assert "unauthorized" in str(err.value)
        assert TEST_KEY not in str(err.value)

    def test_malformed_key_fails_without_a_request(self, api):
        with pytest.raises(ToolProviderCredentialValidationError):
            self.provider().validate_credentials({"okdata_api_key": "not-a-key"})
        assert api.requests == []


class TestIdCleanup:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1", "dQw4w9WgXcQ"),
            ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ],
    )
    def test_youtube(self, raw, expected):
        assert runner.youtube_video_id(raw) == expected

    def test_douyin_short_link_is_passed_through(self):
        assert runner.douyin_video_id("https://v.douyin.com/abc/") == "https://v.douyin.com/abc/"

    def test_douyin_modal_id(self):
        assert runner.douyin_video_id("https://www.douyin.com/discover?modal_id=7301234567890123456") == "7301234567890123456"

    def test_xiaohongshu_plain_id(self):
        assert runner.xiaohongshu_note_id(" 6650a1b2000000001e00abcd ") == "6650a1b2000000001e00abcd"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("7305085486984858894", "7305085486984858894"),
            ("https://www.tiktok.com/@nasa/video/7305085486984858894?is_from_webapp=1", "7305085486984858894"),
            ("https://vm.tiktok.com/ZMabc/", "https://vm.tiktok.com/ZMabc/"),
        ],
    )
    def test_tiktok(self, raw, expected):
        assert runner.tiktok_video_id(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("nasa", "nasa"),
            (" @nasa ", "@nasa"),
            ("https://www.instagram.com/nasa/?hl=en", "nasa"),
            ("https://www.instagram.com/p/DeCPVhERA8e/", "https://www.instagram.com/p/DeCPVhERA8e/"),
        ],
    )
    def test_instagram_handle(self, raw, expected):
        assert runner.instagram_handle(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("DeCPVhERA8e", "DeCPVhERA8e"),
            ("https://www.instagram.com/p/DeCPVhERA8e/?igsh=x", "DeCPVhERA8e"),
            ("https://www.instagram.com/reel/DeC-PVh_8e/", "DeC-PVh_8e"),
            ("https://www.instagram.com/nasa/p/DeCPVhERA8e/", "DeCPVhERA8e"),
        ],
    )
    def test_instagram_shortcode(self, raw, expected):
        assert runner.instagram_shortcode(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("t3_1nnrvkr", "t3_1nnrvkr"),
            ("https://www.reddit.com/r/nasa/comments/1nnrvkr/some_title/", "1nnrvkr"),
            ("https://redd.it/1nnrvkr", "1nnrvkr"),
            ("https://www.reddit.com/r/nasa/s/AbCdEf123", "https://www.reddit.com/r/nasa/s/AbCdEf123"),
        ],
    )
    def test_reddit(self, raw, expected):
        assert runner.reddit_post_id(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("B0GTS6KPPB", "B0GTS6KPPB"),
            ("https://www.amazon.com/dp/B0GTS6KPPB?th=1", "B0GTS6KPPB"),
            ("https://www.amazon.co.uk/gp/product/b0gts6kppb/ref=x", "B0GTS6KPPB"),
            ("https://www.amazon.de/product-reviews/B0GTS6KPPB/", "B0GTS6KPPB"),
            ("https://amzn.to/3abcdef", "https://amzn.to/3abcdef"),
        ],
    )
    def test_amazon(self, raw, expected):
        assert runner.amazon_asin(raw) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("https://www.reddit.com/r/a/s/b", True),
            ("www.instagram.com/p/x/", True),
            ("redd.it/abc", True),
            ("1nnrvkr", False),
            ("t3_1nnrvkr", False),
            ("DeCPVhERA8e", False),
            (None, False),
        ],
    )
    def test_is_link(self, value, expected):
        assert runner.is_link(value) is expected


class TestLinkRouting:
    def test_id_read_from_a_link_goes_as_id(self):
        spec = runner.SPECS["reddit_post_comments"]
        assert runner.api_params(spec, {"id": "https://redd.it/1nnrvkr"}) == {"id": "1nnrvkr"}

    def test_link_without_an_id_goes_as_url(self):
        spec = runner.SPECS["instagram_post_comments"]
        link = "https://instagr.am/share/abc123"
        assert runner.api_params(spec, {"id": link, "cursor": "c1.n"}) == {"url": link, "cursor": "c1.n"}

    def test_plain_id_is_sent_as_id(self):
        spec = runner.SPECS["reddit_post_comments"]
        assert runner.api_params(spec, {"id": "t3_1nnrvkr", "sort": None}) == {"id": "t3_1nnrvkr"}

    def test_tools_without_link_routing_send_links_unchanged(self):
        spec = runner.SPECS["wechat_article_stats"]
        url = "https://mp.weixin.qq.com/s/abc"
        assert runner.api_params(spec, {"url": url}) == {"url": url}
