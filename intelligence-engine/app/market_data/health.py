"""Provider health service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.market_data.circuit_breaker import CircuitBreakerRegistry
from app.market_data.metrics import MarketDataMetrics
from app.market_data.registry import ProviderRegistry


@dataclass
class ProviderHealth:
    provider_id: str
    configured: bool
    circuit_state: str
    capabilities: list[str] = field(default_factory=list)
    last_error: str | None = None
    ok: bool = True


class ProviderHealthService:
    def __init__(
        self,
        registry: ProviderRegistry,
        circuits: CircuitBreakerRegistry,
        metrics: MarketDataMetrics,
    ) -> None:
        self.registry = registry
        self.circuits = circuits
        self.metrics = metrics
        self._last_errors: dict[str, str] = {}

    def record_error(self, provider_id: str, message: str) -> None:
        self._last_errors[provider_id] = message

    def snapshot(self) -> dict[str, object]:
        circuit_states = self.circuits.snapshot()
        metric_snapshot = self.metrics.snapshot()
        successes = metric_snapshot.get("provider_success") or {}
        providers: list[dict[str, object]] = []
        for provider in self.registry.list_providers():
            state = circuit_states.get(provider.provider_id, "closed")
            configured = provider.is_configured()
            verified_requests = int(successes.get(provider.provider_id) or 0)
            available = configured and state != "open"
            row: dict[str, object] = {
                "provider_id": provider.provider_id,
                "configured": configured,
                "circuit_state": state,
                "capabilities": sorted(provider.capabilities()),
                "priority": provider.priority,
                "last_error": self._last_errors.get(provider.provider_id),
                "ok": available,
                "available": available,
                "verified_live": verified_requests > 0,
                "verified_requests": verified_requests,
                "operational_status": (
                    "verified" if verified_requests > 0 else "configured_unverified"
                ) if available else "unavailable",
            }
            # Soft extras (Yahoo health dashboard fields)
            if hasattr(provider, "health_extras"):
                try:
                    row["extras"] = provider.health_extras()  # type: ignore[operator]
                except Exception:
                    pass
            providers.append(row)
        return {
            "ok": any(p["ok"] for p in providers) if providers else False,
            "live_data_verified": any(p["verified_live"] for p in providers) if providers else False,
            "status": (
                "verified" if any(p["verified_live"] for p in providers)
                else "configured_unverified" if any(p["ok"] for p in providers)
                else "unavailable"
            ),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "providers": providers,
            "metrics": metric_snapshot,
        }
