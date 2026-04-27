from voidminer.core.baseline import build_baseline
from voidminer.core.requester import HTTPResult


class FakeRequester:
    def __init__(self) -> None:
        self.calls = 0

    def request(self, method: str, url: str) -> HTTPResult:
        self.calls += 1
        if self.calls == 1:
            body = '{"ok":true,"trace_id":"aaa","epoch":1711111111111}'
            return HTTPResult(url=url, method=method, status_code=200, headers={"content-type": "application/json"}, text=body, content_length=50, response_time_ms=90.0)
        if self.calls == 2:
            body = '{"ok":true,"trace_id":"bbb","epoch":1711111111222}'
            return HTTPResult(url=url, method=method, status_code=200, headers={"content-type": "application/json"}, text=body, content_length=500, response_time_ms=2000.0)
        body = '{"ok":true,"trace_id":"ccc","epoch":1711111111333}'
        return HTTPResult(url=url, method=method, status_code=200, headers={"content-type": "application/json"}, text=body, content_length=52, response_time_ms=100.0)


def test_baseline_uses_median_for_stability() -> None:
    requester = FakeRequester()
    baseline, _samples = build_baseline(requester, "https://example.com/api")
    assert baseline.status_code == 200
    assert baseline.content_length == 52
    assert baseline.response_time_ms == 100.0
