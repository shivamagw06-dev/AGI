"""Downloader — bytes only; never parses (FSE-02 §6.2)."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from typing import Any

from financial_statements_engine.collection.schema import DEFAULT_MIN_INTERVAL_MS

_LAST_HOST_HIT: dict[str, float] = {}


def _user_agent() -> str:
    return os.environ.get("FSE_HTTP_USER_AGENT", "AGIB-FSE-Collector/1.0 (+https://agarwalglobalinvestments.com)")


def _min_interval_s() -> float:
    try:
        ms = float(os.environ.get("FSE_HTTP_MIN_INTERVAL_MS", DEFAULT_MIN_INTERVAL_MS))
    except ValueError:
        ms = float(DEFAULT_MIN_INTERVAL_MS)
    return max(0.0, ms / 1000.0)


def _throttle(url: str) -> None:
    from urllib.parse import urlparse

    host = urlparse(url).netloc or "local"
    gap = _min_interval_s()
    last = _LAST_HOST_HIT.get(host, 0.0)
    wait = gap - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _LAST_HOST_HIT[host] = time.time()


def download_bytes(url: str | None = None, *, data: bytes | None = None, timeout_s: float = 30.0) -> dict[str, Any]:
    """Download URL or accept injected bytes (tests / offline adapters).

    Never parses content.
    """
    if data is not None:
        return {
            "ok": True,
            "bytes": data,
            "url": url,
            "http_status": 200,
            "error": None,
            "layer": "downloader",
        }
    if not url:
        return {"ok": False, "bytes": None, "url": url, "http_status": None, "error": "url_required", "layer": "downloader"}

    _throttle(url)
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200) or 200
            return {
                "ok": True,
                "bytes": body,
                "url": url,
                "http_status": int(status),
                "error": None,
                "layer": "downloader",
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "bytes": None,
            "url": url,
            "http_status": int(exc.code),
            "error": str(exc),
            "layer": "downloader",
        }
    except Exception as exc:  # timeout / connection
        return {
            "ok": False,
            "bytes": None,
            "url": url,
            "http_status": None,
            "error": str(exc),
            "layer": "downloader",
        }
