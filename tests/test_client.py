from __future__ import annotations

import httpx
import pytest

from okdata_api import client
from tests.conftest import TEST_KEY, error_body, ok_envelope


class TestNormalizeApiKey:
    def test_strips_whitespace_and_bearer_prefix(self):
        assert client.normalize_api_key(f"  Bearer {TEST_KEY} ") == TEST_KEY

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_missing_key_is_refused(self, raw):
        with pytest.raises(client.OkdataError) as err:
            client.normalize_api_key(raw)
        assert err.value.code == "missing_key"

    @pytest.mark.parametrize("raw", ["sk-abc", "okd abc", "okd_abc def"])
    def test_malformed_key_is_refused_without_echoing_it(self, raw):
        with pytest.raises(client.OkdataError) as err:
            client.normalize_api_key(raw)
        assert err.value.code == "malformed_key"
        assert raw not in str(err.value)


class TestNormalizeMaxPrice:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(0.05, "0.05"), (0.1, "0.1"), ("0.020", "0.02"), ("$1", "1"), (1e-4, "0.0001"), (5, "5")],
    )
    def test_formats_plain_decimal(self, raw, expected):
        assert client.normalize_max_price(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "  "])
    def test_empty_means_no_cap(self, raw):
        assert client.normalize_max_price(raw) is None

    @pytest.mark.parametrize("raw", [0, -1, "abc", "nan", 1000])
    def test_rejects_bad_values(self, raw):
        with pytest.raises(client.OkdataError) as err:
            client.normalize_max_price(raw)
        assert err.value.code == "invalid_max_price"


class TestRequest:
    def test_paid_call_sends_key_source_cap_and_idempotency_key(self, api):
        api.handler = lambda request: (200, ok_envelope({"items": []}))
        client.request("GET", "/v1/x/posts/search", api_key=TEST_KEY, params={"query": "a b", "sort": None}, max_price="0.01")
        sent = api.last
        assert sent.url.path == "/v1/x/posts/search"
        assert dict(sent.url.params) == {"query": "a b"}
        assert sent.headers["Authorization"] == f"Bearer {TEST_KEY}"
        assert sent.headers["X-Source"] == "dify"
        assert sent.headers["X-Max-Price"] == "0.01"
        assert len(sent.headers["Idempotency-Key"]) == 36

    def test_free_call_sends_no_key_and_no_idempotency_key(self, api):
        api.handler = lambda request: (200, ok_envelope({"endpoints": []}))
        client.request("GET", "/v1/catalog")
        assert "Authorization" not in api.last.headers
        assert "Idempotency-Key" not in api.last.headers
        assert api.last.headers["X-Source"] == "dify"

    def test_account_check_has_no_idempotency_key(self, api):
        api.handler = lambda request: (200, ok_envelope({"balance": "5.00"}))
        client.check_key(TEST_KEY)
        assert api.last.url.path == "/v1/account"
        assert "Idempotency-Key" not in api.last.headers

    def test_list_and_bool_params_are_encoded(self, api):
        api.handler = lambda request: (200, ok_envelope({"items": []}))
        client.request("GET", "/v1/a", api_key=TEST_KEY, params={"fields": ["id", "text"], "flag": True})
        assert dict(api.last.url.params) == {"fields": "id,text", "flag": "true"}

    def test_post_sends_json_body(self, api):
        api.handler = lambda request: (200, ok_envelope({"items": []}))
        client.request("POST", "/v1/a", api_key=TEST_KEY, body={"ids": ["1", "2"]})
        assert api.last.method == "POST"
        assert api.last.read() == b'{"ids":["1","2"]}'

    def test_error_envelope_raises_readable_error_without_the_key(self, api):
        body = error_body(
            "insufficient_balance",
            "Not enough balance for this call",
            problems=["Needs 0.02, balance 0.01."],
            next_step="Top up at https://okdata.online/console/",
        )
        api.handler = lambda request: (402, body)
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        text = str(err.value)
        assert err.value.code == "insufficient_balance"
        assert "HTTP 402" in text and "Needs 0.02" in text and "Top up" in text
        assert "Nothing was billed." in text
        assert "a5b48f50-c209-4cad-a455-19421ec36ee5" in text
        assert TEST_KEY not in text

    def test_unknown_billing_state_is_stated(self, api):
        api.handler = lambda request: (502, error_body("settlement_unknown", "Lost answer", charged=None))
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert "not known yet" in str(err.value)

    def test_retries_once_with_the_same_idempotency_key(self, api):
        answers = iter([(503, error_body("internal_error", "Busy", retry="yes", retry_after_seconds=1)), (200, ok_envelope({"items": []}))])
        api.handler = lambda request: next(answers)
        envelope = client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert envelope["code"] == "ok"
        assert len(api.requests) == 2
        assert api.requests[0].headers["Idempotency-Key"] == api.requests[1].headers["Idempotency-Key"]

    def test_does_not_retry_when_told_not_to(self, api):
        api.handler = lambda request: (400, error_body("invalid_params", "Bad", retry="after_fix"))
        with pytest.raises(client.OkdataError):
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert len(api.requests) == 1

    def test_does_not_wait_long_for_rate_limits(self, api):
        api.handler = lambda request: (429, error_body("rate_limited", "Slow down", retry="yes", retry_after_seconds=30))
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert err.value.code == "rate_limited"
        assert len(api.requests) == 1

    def test_connection_failure_after_retry(self, api):
        def fail(request):
            raise httpx.ConnectError("boom", request=request)

        api.handler = fail
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert err.value.code == "connection_error"
        assert err.value.billed is False
        assert len(api.requests) == 2

    def test_read_timeout_is_not_retried_and_billing_is_unknown(self, api):
        def slow(request):
            raise httpx.ReadTimeout("slow", request=request)

        api.handler = slow
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert err.value.code == "client_timeout"
        assert err.value.billed is None
        assert "not known yet" in str(err.value)
        assert len(api.requests) == 1

    def test_non_json_answer(self, api):
        api.handler = lambda request: (502, "<html>bad gateway</html>")
        with pytest.raises(client.OkdataError) as err:
            client.request("GET", "/v1/a", api_key=TEST_KEY)
        assert err.value.code == "bad_response"
