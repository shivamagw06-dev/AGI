"""Read Knowledge Objects / Bundles from KAIP/KRIG internal APIs.

The Intelligence Engine must never call Yahoo/NSE/BSE directly for knowledge supply.
Sprint 6.4: KRIG delivers Knowledge Bundles — Ask performs zero data discovery.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class KaipClientError(RuntimeError):
    pass


class KaipClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("KAIP_BASE_URL") or "http://127.0.0.1:8091").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                resp = self._client.get(url, timeout=self.timeout_seconds)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.get(url)
        except httpx.HTTPError as exc:
            raise KaipClientError(f"kaip_unreachable:{exc}") from exc
        if resp.status_code == 404:
            raise KaipClientError("kaip_not_found")
        if resp.status_code >= 400:
            raise KaipClientError(f"kaip_http_{resp.status_code}")
        data = resp.json()
        if not isinstance(data, dict):
            raise KaipClientError("kaip_invalid_payload")
        return data

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                resp = self._client.post(url, json=body, timeout=self.timeout_seconds)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(url, json=body)
        except httpx.HTTPError as exc:
            raise KaipClientError(f"kaip_unreachable:{exc}") from exc
        if resp.status_code >= 400:
            raise KaipClientError(f"kaip_http_{resp.status_code}")
        data = resp.json()
        if not isinstance(data, dict):
            raise KaipClientError("kaip_invalid_payload")
        return data

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Return institutional CompanyProfile (includes company_knowledge view)."""
        return self._get(f"/v1/knowledge/company/{symbol.upper()}")

    def get_company_knowledge(self, symbol: str) -> dict[str, Any]:
        """Convenience: Company Knowledge projection only (never provider JSON)."""
        profile = self.get_company_profile(symbol)
        view = profile.get("company_knowledge")
        if not isinstance(view, dict):
            raise KaipClientError("kaip_missing_company_knowledge")
        return view

    def get_relationships(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/relationships/{symbol.upper()}")

    def get_sector_knowledge(self, sector_key: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/sector/{sector_key}")

    def get_memory(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/memory/{symbol.upper()}")

    def get_timeline(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/timeline/{symbol.upper()}")

    def get_conflicts(self, symbol: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/conflicts/{symbol.upper()}")

    def get_sector_learning(self, sector_key: str) -> dict[str, Any]:
        return self._get(f"/v1/knowledge/sector-learning/{sector_key}")

    def get_market_learning(self) -> dict[str, Any]:
        return self._get("/v1/knowledge/market-learning")

    def health(self) -> dict[str, Any]:
        return self._get("/healthz")


class KrigClient(KaipClient):
    """Sprint 6.4 — Knowledge Retrieval & Intelligence Gateway client.

    Ask / IE should prefer Knowledge Bundles over piecemeal KO fetches.
    """

    def retrieve_bundle(
        self,
        *,
        question: str | None = None,
        symbols: list[str] | None = None,
        sector_key: str | None = None,
        query_type: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        return self._post(
            "/v1/knowledge/bundle",
            {
                "question": question,
                "symbols": symbols,
                "sector_key": sector_key,
                "query_type": query_type,
                "use_cache": use_cache,
            },
        )

    def company_bundle(self, symbol: str, *, question: str | None = None) -> dict[str, Any]:
        path = f"/v1/knowledge/bundle/company/{symbol.upper()}"
        if question:
            from urllib.parse import quote

            path = f"{path}?question={quote(question)}"
        return self._get(path)

    def compare(self, symbols: list[str], *, question: str | None = None) -> dict[str, Any]:
        return self._post(
            "/v1/knowledge/compare",
            {"symbols": [s.upper() for s in symbols], "question": question},
        )

    def macro(self, *, question: str | None = None) -> dict[str, Any]:
        path = "/v1/knowledge/macro"
        if question:
            from urllib.parse import quote

            path = f"{path}?question={quote(question)}"
        return self._get(path)

    def market(self, *, question: str | None = None) -> dict[str, Any]:
        path = "/v1/knowledge/market"
        if question:
            from urllib.parse import quote

            path = f"{path}?question={quote(question)}"
        return self._get(path)
