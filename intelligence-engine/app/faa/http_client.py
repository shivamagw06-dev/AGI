"""Shared HTTP client — retry, exponential backoff, timeouts, rate limiting."""

from __future__ import annotations

import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class HttpResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]
    url: str
    elapsed_ms: float
    attempts: int = 1
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        return (self.content or b"").decode("utf-8", errors="ignore")

    def header(self, name: str) -> str | None:
        target = name.lower()
        for k, v in self.headers.items():
            if k.lower() == target:
                return v
        return None


class RateLimiter:
    """Simple sliding-window rate limiter per connector."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self.rate_limit_events = 0

    def wait(self, key: str, *, max_per_minute: int = 30) -> None:
        if max_per_minute <= 0:
            return
        with self._lock:
            now = time.time()
            q = self._events[key]
            while q and now - q[0] > 60.0:
                q.popleft()
            if len(q) >= max_per_minute:
                sleep_for = 60.0 - (now - q[0]) + 0.05
                self.rate_limit_events += 1
            else:
                sleep_for = 0.0
            if sleep_for > 0:
                # release lock while sleeping
                pass
            else:
                q.append(now)
                return
        time.sleep(min(sleep_for, 5.0))
        with self._lock:
            now = time.time()
            q = self._events[key]
            while q and now - q[0] > 60.0:
                q.popleft()
            q.append(now)


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 25.0,
        max_retries: int = 3,
        backoff_base: float = 0.4,
        user_agent: str = "AGIB-FAA/1.0 (+https://agarwalglobalinvestments.com)",
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter()
        self._lock = threading.Lock()
        self.requests_total = 0
        self.failures_total = 0

    def get(
        self,
        url: str,
        *,
        connector_id: str = "default",
        headers: dict[str, str] | None = None,
        max_per_minute: int = 30,
        conditional: dict[str, str] | None = None,
    ) -> HttpResponse:
        self.rate_limiter.wait(connector_id, max_per_minute=max_per_minute)
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if headers:
            req_headers.update(headers)
        if conditional:
            if conditional.get("etag"):
                req_headers["If-None-Match"] = conditional["etag"]
            if conditional.get("last_modified"):
                req_headers["If-Modified-Since"] = conditional["last_modified"]

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                import httpx

                with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=req_headers) as client:
                    resp = client.get(url)
                elapsed = (time.perf_counter() - t0) * 1000
                with self._lock:
                    self.requests_total += 1
                headers_out = {k: v for k, v in resp.headers.items()}
                # Never retry permanent failures (401/402/403/404).
                if resp.status_code in {401, 402, 403, 404}:
                    return HttpResponse(
                        status_code=resp.status_code,
                        content=resp.content or b"",
                        headers=headers_out,
                        url=str(resp.url),
                        elapsed_ms=elapsed,
                        attempts=attempt,
                    )
                # Retry only transient: 429 / 5xx
                if resp.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
                return HttpResponse(
                    status_code=resp.status_code,
                    content=resp.content or b"",
                    headers=headers_out,
                    url=str(resp.url),
                    elapsed_ms=elapsed,
                    attempts=attempt,
                )
            except Exception as exc:
                last_exc = exc
                with self._lock:
                    self.failures_total += 1
                if attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
        return HttpResponse(
            status_code=0,
            content=b"",
            headers={},
            url=url,
            elapsed_ms=0.0,
            attempts=self.max_retries,
            error=str(last_exc) if last_exc else "request_failed",
        )

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        connector_id: str = "search_api",
        headers: dict[str, str] | None = None,
        max_per_minute: int = 20,
    ) -> HttpResponse:
        self.rate_limiter.wait(connector_id, max_per_minute=max_per_minute)
        req_headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                import httpx

                with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=req_headers) as client:
                    resp = client.post(url, json=payload)
                elapsed = (time.perf_counter() - t0) * 1000
                with self._lock:
                    self.requests_total += 1
                headers_out = {k: v for k, v in resp.headers.items()}
                if resp.status_code in {401, 402, 403, 404}:
                    return HttpResponse(
                        status_code=resp.status_code,
                        content=resp.content or b"",
                        headers=headers_out,
                        url=str(resp.url),
                        elapsed_ms=elapsed,
                        attempts=attempt,
                    )
                if resp.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
                return HttpResponse(
                    status_code=resp.status_code,
                    content=resp.content or b"",
                    headers=headers_out,
                    url=str(resp.url),
                    elapsed_ms=elapsed,
                    attempts=attempt,
                )
            except Exception as exc:
                last_exc = exc
                with self._lock:
                    self.failures_total += 1
                if attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
        return HttpResponse(
            status_code=0,
            content=b"",
            headers={},
            url=url,
            elapsed_ms=0.0,
            attempts=self.max_retries,
            error=str(last_exc) if last_exc else "request_failed",
        )

    def _backoff(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.2)
        time.sleep(min(delay, 8.0))

    def stats(self) -> dict[str, Any]:
        return {
            "requests_total": self.requests_total,
            "failures_total": self.failures_total,
            "rate_limit_events": self.rate_limiter.rate_limit_events,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
