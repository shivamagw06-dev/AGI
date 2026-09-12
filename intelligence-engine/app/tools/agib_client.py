from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.resilience.circuit_breaker import get_provider_circuits
from app.resilience.policy import classify_http_status, RetryDecision

log = get_logger(__name__)


class AgibClient:
    """Read-only client for AGIB Node cached endpoints. Never call third-party APIs here."""

    def __init__(self, base_url: str | None = None, timeout: float = 3.0):
        settings = get_settings()
        base = (base_url or settings.agib_api_base_url).rstrip("/")
        if base and not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        self.base_url = base
        # Ask-path budget: connect+read must stay inside ~2–3s per hop.
        self.timeout = httpx.Timeout(connect=1.5, read=timeout, write=timeout, pool=1.5)
        self.token = settings.agib_service_token
        self.provider_id = "agib_node"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_json(self, path: str) -> dict[str, Any] | None:
        url = f"{self.base_url}{path}"
        circuits = get_provider_circuits()
        if not circuits.allow(self.provider_id):
            log.warning("agib_circuit_open", extra={"url": url})
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._headers())
                if response.status_code >= 400:
                    decision = classify_http_status(response.status_code)
                    # Permanent auth/billing/not-found — never retry; trip circuit.
                    if decision is RetryDecision.NEVER:
                        circuits.failure(
                            self.provider_id,
                            error=f"HTTP {response.status_code}",
                            status=response.status_code,
                        )
                    elif decision is RetryDecision.TRANSIENT:
                        circuits.failure(
                            self.provider_id,
                            error=f"HTTP {response.status_code}",
                            status=response.status_code,
                        )
                    log.warning(
                        "agib_fetch_failed",
                        extra={
                            "url": url,
                            "status": response.status_code,
                            "retryable": decision is RetryDecision.TRANSIENT,
                        },
                    )
                    return None
                circuits.success(self.provider_id)
                return response.json()
        except Exception as exc:
            circuits.failure(self.provider_id, error=str(exc)[:200])
            log.warning("agib_fetch_error", extra={"url": url, "error": str(exc)})
            return None

    async def macro_briefing(self) -> dict[str, Any] | None:
        return await self.get_json("/api/market/macro-briefing")

    async def market_briefing(self) -> dict[str, Any] | None:
        return await self.get_json("/api/market/briefing")

    async def pre_market_briefing(self) -> dict[str, Any] | None:
        return await self.get_json("/api/market/pre-market-briefing")

    async def market_context(self) -> dict[str, Any] | None:
        return await self.get_json("/api/market-context")
