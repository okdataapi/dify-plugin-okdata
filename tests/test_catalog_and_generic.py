from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from okdata_api import catalog, client, generic, runner, summary
from tests.conftest import ROOT, TEST_KEY, collect, ok_envelope
from tests.test_tools import run_tool


def catalog_then(catalog_body, answer):
    """Handler: the catalog for /v1/catalog, `answer` for anything else."""

    def handler(request):
        if request.url.path == "/v1/catalog":
            return 200, catalog_body
        return answer(request)

    return handler


class TestFind:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("抖音 评论", "douyin.videos.comments.list"),
            ("rednote search", "xiaohongshu.notes.search"),
            ("tweets", "x.posts.search"),
            ("微博 热搜", "weibo.trends.list"),
            ("youtube subtitles", "youtube.videos.transcript.get"),
            ("公众号 阅读数", "wechat_mp.articles.metrics"),
        ],
    )
    def test_best_match(self, catalog_body, query, expected):
        found = catalog.find_endpoints(catalog_body["data"], query, limit=3)
        assert found and found[0]["id"] == expected, [f["id"] for f in found]

    def test_platform_filter(self, catalog_body):
        found = catalog.find_endpoints(catalog_body["data"], "comments", platform="douyin")
        assert {f["platform"] for f in found} == {"douyin"}

    def test_nothing_matches(self, catalog_body):
        assert catalog.find_endpoints(catalog_body["data"], "zzzzqqq") == []

    def test_find_tool_is_free_and_sends_no_key(self, api, catalog_body):
        api.handler = lambda request: (200, catalog_body)
        out = run_tool("find_endpoint", {"query": "bilibili popular", "limit": 3})
        assert [r.url.path for r in api.requests] == ["/v1/catalog"]
        assert "Authorization" not in api.last.headers
        assert out["variables"]["endpoints"][0]["id"] == "bilibili.trends.list"
        assert "bilibili.trends.list" in out["text"][0]
        assert "okdata.online/apis/bilibili/trends/list/" in out["text"][0]

    def test_catalog_is_cached(self, api, catalog_body):
        api.handler = lambda request: (200, catalog_body)
        run_tool("find_endpoint", {"query": "weibo"})
        run_tool("find_endpoint", {"query": "douyin"})
        assert len(api.requests) == 1

    def test_describe_hides_view_and_fields(self, catalog_body):
        endpoint = catalog.get_endpoint(catalog_body["data"], "douyin.videos.search")
        names = [p["name"] for p in catalog.describe(endpoint)["params"]]
        assert "query" in names and "view" not in names and "fields" not in names


class TestCallEndpoint:
    def test_calls_by_id_with_json_params(self, api, catalog_body):
        api.handler = catalog_then(catalog_body, lambda r: (200, ok_envelope({"items": [{"rank": 1, "name": "topic", "heat": 1200, "url": None}]})))
        out = run_tool("call_endpoint", {"endpoint_id": "/v1/bilibili/trends/list", "params": "{}", "view": "compact", "max_price": 0.02})
        sent = api.last
        assert sent.url.path == "/v1/bilibili/trends/list"
        assert dict(sent.url.params) == {"view": "compact"}
        assert sent.headers["X-Max-Price"] == "0.02"
        assert sent.headers["Authorization"] == f"Bearer {TEST_KEY}"
        assert "1. topic (heat 1.2k)" in out["text"][0]

    def test_params_max_price_cannot_raise_the_cap(self, api, catalog_body):
        api.handler = catalog_then(catalog_body, lambda r: (200, ok_envelope({"items": []})))
        out = run_tool("call_endpoint", {"endpoint_id": "x.posts.search", "params": json.dumps({"query": "a", "max_price": "50"})})
        assert dict(api.last.url.params) == {"query": "a"}
        assert api.last.headers["X-Max-Price"] == generic.DEFAULT_MAX_PRICE
        assert "max_price in params was ignored" in out["text"][0]

    def test_unknown_endpoint_suggests_close_ones_and_makes_no_paid_call(self, api, catalog_body):
        api.handler = lambda request: (200, catalog_body)
        with pytest.raises(client.OkdataError) as err:
            run_tool("call_endpoint", {"endpoint_id": "douyin.video.comments"})
        assert err.value.code == "unknown_endpoint"
        assert "douyin.videos.comments.list" in str(err.value)
        assert [r.url.path for r in api.requests] == ["/v1/catalog"]

    @pytest.mark.parametrize("raw", ["{bad", "[1, 2]", '{"a": {"b": 1}}'])
    def test_bad_params_are_refused(self, api, raw):
        with pytest.raises(client.OkdataError) as err:
            run_tool("call_endpoint", {"endpoint_id": "x.posts.search", "params": raw})
        assert err.value.code == "invalid_params"
        assert api.requests == []

    def test_normalize_endpoint_id(self):
        assert catalog.normalize_endpoint_id("https://api.okdata.online/v1/douyin/videos/search?query=a") == "douyin.videos.search"
        assert catalog.normalize_endpoint_id(" douyin.videos.search ") == "douyin.videos.search"


class TestSummary:
    def test_comments(self):
        envelope = ok_envelope({"items": [{"id": "c1", "text": "nice", "author": {"name": "Ann"}, "likes": 1500, "replies": 3}]})
        text = summary.summarize("Comments", envelope)
        assert "1. nice | Ann | 1.5k likes | 3 replies" in text
        assert "Cost: $0.002, balance left: $4.998." in text

    def test_transcript(self):
        item = {"video_id": "v", "lang": "en", "segments": [{"start": 0, "end": 1, "text": "hi"}], "text": "hi there"}
        text = summary.summarize("YouTube transcript", ok_envelope({"item": item}))
        assert "language en, 1 segments" in text and "hi there" in text

    def test_empty_and_next_page(self):
        envelope = ok_envelope({"items": []}, page={"has_more": True, "next_cursor": "c1.n"})
        envelope["meta"]["result_status"] = "empty"
        text = summary.summarize("Search", envelope)
        assert "0 results" in text and "returned nothing" in text and "cursor = c1.n" in text

    def test_low_balance_is_flagged(self):
        envelope = ok_envelope({"items": []})
        envelope["meta"]["billing"]["covers_next"] = False
        assert "will not cover another call" in summary.summarize("Search", envelope)


class TestPackageConsistency:
    def tool_yaml(self, name: str) -> dict:
        return yaml.safe_load((ROOT / "tools" / f"{name}.yaml").read_text(encoding="utf-8"))

    def test_provider_lists_every_tool_file(self):
        provider = yaml.safe_load((ROOT / "provider" / "okdata.yaml").read_text(encoding="utf-8"))
        listed = {Path(p).stem for p in provider["tools"]}
        on_disk = {p.stem for p in (ROOT / "tools").glob("*.yaml")}
        assert listed == on_disk == set(runner.SPECS) | {"find_endpoint", "call_endpoint"}

    @pytest.mark.parametrize("name", sorted(runner.SPECS))
    def test_yaml_inputs_match_spec_and_cap(self, name):
        spec = runner.SPECS[name]
        doc = self.tool_yaml(name)
        params = {p["name"]: p for p in doc["parameters"]}
        assert set(params) == set(spec.params) | {"max_price"}
        assert Decimal(str(params["max_price"]["default"])) == Decimal(spec.max_price)
        assert params["max_price"]["form"] == "form"  # an agent cannot raise its own cap

    def test_call_endpoint_cap_matches(self):
        params = {p["name"]: p for p in self.tool_yaml("call_endpoint")["parameters"]}
        assert Decimal(str(params["max_price"]["default"])) == Decimal(generic.DEFAULT_MAX_PRICE)
        assert params["max_price"]["form"] == "form"

    @pytest.mark.parametrize("path", sorted((ROOT / "tools").glob("*.yaml")), ids=lambda p: p.stem)
    def test_every_label_has_english_and_chinese(self, path):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc["identity"]["label"].keys() >= {"en_US", "zh_Hans"}
        assert doc["description"]["human"].keys() >= {"en_US", "zh_Hans"}
        for param in doc["parameters"]:
            assert param["label"].keys() >= {"en_US", "zh_Hans"}
            assert param["human_description"].keys() >= {"en_US", "zh_Hans"}

    def test_spec_endpoints_exist_in_catalog(self, catalog_body):
        ids = {e["id"] for e in catalog_body["data"]["endpoints"]}
        for spec in runner.SPECS.values():
            assert spec.endpoint_id in ids
            endpoint = catalog.get_endpoint(catalog_body["data"], spec.endpoint_id)
            api_params = {p["name"] for p in endpoint["params"]}
            assert set(spec.params) <= api_params, spec.endpoint_id
            assert Decimal(endpoint["maxCharge"]) <= Decimal(spec.max_price), spec.endpoint_id
