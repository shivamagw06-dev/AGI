"""Optional soft bridge to HIP historical intelligence — store only, never live providers."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("ifi.hip")


class HipForecastBridge:
    def __init__(self, base_url: str | None = None, *, timeout_seconds: float = 3.0) -> None:
        raw = base_url or os.getenv("IFI_HIP_BASE_URL") or os.getenv("HIP_BASE_URL") or ""
        self.base_url = raw.rstrip("/") or None
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def company_history(self, symbol: str) -> dict[str, Any] | None:
        return self._get(f"/v1/history/company/{symbol.upper()}")

    def company_timeline(self, symbol: str) -> dict[str, Any] | None:
        return self._get(f"/v1/history/timeline/{symbol.upper()}")

    def company_relationships(self, symbol: str) -> dict[str, Any] | None:
        return self._get(f"/v1/history/relationships/company/{symbol.upper()}")

    def company_analogues(self, symbol: str, *, question: str | None = None) -> dict[str, Any] | None:
        q = question or "Has this company experienced a similar situation before?"
        return self._post(
            "/v1/history/analogues/search",
            {"scope": "company", "entity": symbol.upper(), "question": q, "top_k": 5},
        )

    def macro_relationships(self, event: str = "rbi_rate_cut") -> dict[str, Any] | None:
        return self._get(f"/v1/history/relationships/macro/{event}")

    def _get(self, path: str) -> dict[str, Any] | None:
        if not self.base_url:
            return None
        try:
            req = urllib.request.Request(
                f"{self.base_url}{path}", method="GET", headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.info("HIP bridge miss path=%s err=%s", path, exc)
            return None

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.base_url:
            return None
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}{path}",
                data=data,
                method="POST",
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.info("HIP bridge miss path=%s err=%s", path, exc)
            return None
