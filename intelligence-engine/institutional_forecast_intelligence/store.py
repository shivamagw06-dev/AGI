"""In-process IFI metrics store for Mission Control."""

from __future__ import annotations

import time
from typing import Any


class IfiMetricsStore:
    def __init__(self) -> None:
        self._generations: list[dict[str, Any]] = []

    def record(self, *, scope: str, entity: str, completeness_score: float, latency_ms: float, ok: bool) -> None:
        self._generations.append(
            {
                "scope": scope,
                "entity": entity,
                "completeness_score": completeness_score,
                "latency_ms": latency_ms,
                "ok": ok,
                "ts": time.time(),
            }
        )
        if len(self._generations) > 500:
            del self._generations[:-500]

    def dashboard(self) -> dict[str, Any]:
        gens = self._generations
        n = len(gens)
        ok_n = sum(1 for g in gens if g.get("ok"))
        avg_c = round(sum(float(g.get("completeness_score") or 0) for g in gens) / n, 4) if n else 0.0
        avg_l = round(sum(float(g.get("latency_ms") or 0) for g in gens) / n, 2) if n else 0.0
        by_scope: dict[str, int] = {}
        for g in gens:
            by_scope[g["scope"]] = by_scope.get(g["scope"], 0) + 1
        return {
            "forecast_bundle_generations": n,
            "bundle_generation_success_rate": round(ok_n / n, 4) if n else None,
            "average_knowledge_completeness": avg_c,
            "average_retrieval_latency_ms": avg_l,
            "generations_by_scope": by_scope,
            "recent": list(reversed(gens[-15:])),
        }


METRICS = IfiMetricsStore()
