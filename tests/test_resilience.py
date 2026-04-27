from urllib.parse import parse_qs, urlparse

import httpx

from voidminer.core.requester import HTTPRequestError, Requester
from voidminer.modes.query_miner import run_query_miner


def _all_timeout_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timeout", request=request)


def _partial_failure_handler(request: httpx.Request) -> httpx.Response:
    parsed = urlparse(str(request.url))
    query = parse_qs(parsed.query)
    if not query:
        return httpx.Response(
            status_code=200,
            headers={"content-type": "application/json"},
            text='{"ok":true,"trace_id":"abc123"}',
            request=request,
        )
    if "timeout" in query:
        raise httpx.ReadTimeout("timeout", request=request)
    key = next(iter(query.keys()))
    value = query.get(key, [""])[0]
    return httpx.Response(
        status_code=200,
        headers={"content-type": "application/json", "x-debug": "enabled"},
        text=f'{{"ok":true,"{key}":"{value}"}}',
        request=request,
    )


def test_requester_wraps_httpx_errors() -> None:
    requester = Requester(timeout=0.1, rate=1000.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(_all_timeout_handler), follow_redirects=True)
    try:
        try:
            requester.request("GET", "https://target.local/api")
        except HTTPRequestError as exc:
            assert "failed" in str(exc)
            assert exc.method == "GET"
        else:
            raise AssertionError("Expected HTTPRequestError")
    finally:
        requester.close()


def test_query_miner_continues_when_some_workers_fail() -> None:
    requester = Requester(timeout=0.1, rate=1000.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(_partial_failure_handler), follow_redirects=True)
    try:
        findings, tested_params, errors_count, endpoint_stats, scan_metrics = run_query_miner(
            requester=requester,
            urls=["https://target.local/api/user"],
            wordlist=["ok", "timeout"],
            method="GET",
            headers={},
            min_score=3,
            threads=2,
            payload_profile="fast",
            max_payloads_per_param=2,
            early_stop_on_strong_signal=True,
        )
    finally:
        requester.close()

    assert tested_params == 2
    assert errors_count == 1
    assert len(findings) == 1
    assert findings[0].parameter == "ok"
    assert endpoint_stats["https://target.local/api/user"]["request_errors"] == 1
    assert scan_metrics["payloads_executed"] >= 1


def test_requester_retries_and_recovers_on_transient_error() -> None:
    state = {"calls": 0}

    def flaky_handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(status_code=200, text="ok", request=request)

    requester = Requester(timeout=0.1, rate=1000.0, max_retries=1, retry_backoff_ms=0.0, retry_jitter_ms=0.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(flaky_handler), follow_redirects=True)
    try:
        response = requester.request("GET", "https://target.local/api")
    finally:
        requester.close()

    assert response.status_code == 200
    assert state["calls"] == 2


def test_requester_retries_on_5xx_status() -> None:
    state = {"calls": 0}

    def flaky_5xx_handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(status_code=503, text="unavailable", request=request)
        return httpx.Response(status_code=200, text="ok", request=request)

    requester = Requester(timeout=0.1, rate=1000.0, max_retries=1, retry_backoff_ms=0.0, retry_jitter_ms=0.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(flaky_5xx_handler), follow_redirects=True)
    try:
        response = requester.request("GET", "https://target.local/api")
    finally:
        requester.close()

    assert response.status_code == 200
    assert state["calls"] == 2


def test_requester_honors_retry_after_header(monkeypatch) -> None:
    state = {"calls": 0, "slept": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(status_code=429, headers={"retry-after": "0.2"}, text="rate limited", request=request)
        return httpx.Response(status_code=200, text="ok", request=request)

    def fake_sleep(seconds: float) -> None:
        state["slept"].append(seconds)

    monkeypatch.setattr("voidminer.core.requester.time.sleep", fake_sleep)
    requester = Requester(timeout=0.1, rate=1000.0, max_retries=1, retry_backoff_ms=50.0, retry_jitter_ms=0.0)
    requester.client.close()
    requester.client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    try:
        response = requester.request("GET", "https://target.local/api")
    finally:
        requester.close()

    assert response.status_code == 200
    assert state["calls"] == 2
    assert requester.retry_attempts == 1
    assert state["slept"]
    assert abs(state["slept"][0] - 0.2) < 0.001
