from __future__ import annotations

import threading
import time
import random
from email.utils import parsedate_to_datetime
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

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


@dataclass
class HTTPRequestError(Exception):
    url: str
    method: str
    message: str
    response_time_ms: float

    def __str__(self) -> str:
        return f"{self.method} {self.url} failed: {self.message}"


class Requester:
    def __init__(
        self,
        timeout: float = 10.0,
        rate: float = 5.0,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        verify: bool = True,
        max_retries: int = 0,
        retry_backoff_ms: float = 200.0,
        retry_jitter_ms: float = 100.0,
    ) -> None:
        self.timeout = timeout
        self.min_interval = 1.0 / rate if rate > 0 else 0.0
        self.max_retries = max(0, max_retries)
        self.retry_backoff_ms = max(0.0, retry_backoff_ms)
        self.retry_jitter_ms = max(0.0, retry_jitter_ms)
        self._lock = threading.Lock()
        self._last_request_ts = 0.0
        self._retry_attempts = 0
        self._retry_attempts_by_endpoint: dict[str, int] = defaultdict(int)
        self.client = httpx.Client(timeout=timeout, headers=headers or {}, proxy=proxy, verify=verify, follow_redirects=True)

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    def _sleep_retry_backoff(self, attempt: int) -> None:
        backoff = self.retry_backoff_ms * (2 ** max(0, attempt - 1))
        jitter = random.uniform(0.0, self.retry_jitter_ms)
        sleep_s = (backoff + jitter) / 1000.0
        if sleep_s > 0:
            time.sleep(sleep_s)

    @staticmethod
    def _parse_retry_after_seconds(value: str | None) -> float | None:
        if not value:
            return None
        try:
            seconds = float(value.strip())
            return max(0.0, seconds)
        except ValueError:
            pass
        try:
            retry_at = parsedate_to_datetime(value)
            now = time.time()
            delay = retry_at.timestamp() - now
            return max(0.0, delay)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _endpoint_key(url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _increment_retry_attempts(self, url: str) -> None:
        endpoint = self._endpoint_key(url)
        with self._lock:
            self._retry_attempts += 1
            self._retry_attempts_by_endpoint[endpoint] += 1

    @property
    def retry_attempts(self) -> int:
        with self._lock:
            return self._retry_attempts

    @property
    def retry_attempts_by_endpoint(self) -> dict[str, int]:
        with self._lock:
            return dict(self._retry_attempts_by_endpoint)

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
        method_upper = method.upper()
        last_error: HTTPRequestError | None = None
        for attempt in range(self.max_retries + 1):
            self._wait_for_rate_limit()
            start = now_ms()
            try:
                response = self.client.request(method=method_upper, url=url, headers=headers)
                elapsed = now_ms() - start
                body = response.text
                if self._is_retryable_status(response.status_code) and attempt < self.max_retries:
                    self._increment_retry_attempts(url)
                    retry_after = self._parse_retry_after_seconds(response.headers.get("retry-after"))
                    if retry_after is not None:
                        time.sleep(retry_after)
                    else:
                        self._sleep_retry_backoff(attempt + 1)
                    continue
                return HTTPResult(
                    url=str(response.request.url),
                    method=method_upper,
                    status_code=response.status_code,
                    headers={k.lower(): v for k, v in response.headers.items()},
                    text=body,
                    content_length=len(body.encode("utf-8", errors="ignore")),
                    response_time_ms=elapsed,
                )
            except httpx.HTTPError as exc:
                elapsed = now_ms() - start
                last_error = HTTPRequestError(
                    url=url,
                    method=method_upper,
                    message=str(exc),
                    response_time_ms=elapsed,
                )
                if attempt < self.max_retries:
                    self._increment_retry_attempts(url)
                    self._sleep_retry_backoff(attempt + 1)
                    continue
                raise last_error from exc
        if last_error:
            raise last_error
        raise HTTPRequestError(url=url, method=method_upper, message="Unknown request failure", response_time_ms=0.0)

    def close(self) -> None:
        self.client.close()
