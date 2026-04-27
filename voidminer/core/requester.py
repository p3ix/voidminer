from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import httpx

from voidminer.utils.timing import now_ms


@dataclass
class HTTPResult:
    url: str
    method: str
    status_code: int
    headers: dict[str, str]
    text: str
    content_length: int
    response_time_ms: float


class Requester:
    def __init__(
        self,
        timeout: float = 10.0,
        rate: float = 5.0,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        verify: bool = True,
    ) -> None:
        self.timeout = timeout
        self.min_interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = threading.Lock()
        self._last_request_ts = 0.0
        self.client = httpx.Client(timeout=timeout, headers=headers or {}, proxy=proxy, verify=verify, follow_redirects=True)

    def _wait_for_rate_limit(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delta = now - self._last_request_ts
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last_request_ts = time.monotonic()

    def request(self, method: str, url: str, headers: dict[str, str] | None = None) -> HTTPResult:
        self._wait_for_rate_limit()
        start = now_ms()
        response = self.client.request(method=method.upper(), url=url, headers=headers)
        elapsed = now_ms() - start
        body = response.text
        return HTTPResult(
            url=str(response.request.url),
            method=method.upper(),
            status_code=response.status_code,
            headers={k.lower(): v for k, v in response.headers.items()},
            text=body,
            content_length=len(body.encode("utf-8", errors="ignore")),
            response_time_ms=elapsed,
        )

    def close(self) -> None:
        self.client.close()
