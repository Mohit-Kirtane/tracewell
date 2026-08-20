import httpx
import pytest

from tracewell_sdk.client import TracewellClient


def test_start_trace_posts_name_and_returns_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/traces"
        assert request.headers["authorization"] == "Bearer tw_test"
        return httpx.Response(200, json={"id": "trace-abc"})

    client = TracewellClient(api_key="tw_test", transport=httpx.MockTransport(handler))
    trace_id = client.start_trace(name="my-run")
    assert trace_id == "trace-abc"


def test_update_trace_patches_status_and_spans():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        return httpx.Response(200, json={"ok": True})

    client = TracewellClient(api_key="tw_test", transport=httpx.MockTransport(handler))
    client.update_trace("trace-abc", status="complete", spans=[{"id": "s1"}])

    assert captured["method"] == "PATCH"
    assert captured["path"] == "/api/v1/traces/trace-abc"


def test_start_trace_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid API key"})

    client = TracewellClient(api_key="tw_bad", transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        client.start_trace(name="my-run")
