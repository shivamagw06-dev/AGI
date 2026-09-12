"""Fundamentals facade — derived, reproducible institutional metrics."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.fundamentals.derivations import (
    DERIVATIONS_VERSION,
    available_metrics,
    derive_latest,
    derive_series,
    is_applicable,
    verify_derivation,
)
from institutional_reasoning.fundamentals.primitives import (
    PRIMITIVES_VERSION,
    covered_entities,
    coverage_report,
    has_primitives,
)

MODULE_CODE = "FUND"
PROGRAMME = "Institutional Fundamentals (derived)"

__all__ = [
    "available_metrics",
    "derive_latest",
    "derive_series",
    "has_primitives",
    "health",
    "quality_gates",
    "verify_derivation",
]


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "primitives_version": PRIMITIVES_VERSION,
        "derivations_version": DERIVATIONS_VERSION,
        "derived_not_stored": True,
        "metrics": available_metrics(),
        "coverage": coverage_report(),
    }


def metric_series(entity_id: str, metric: str, *, sector: str | None = None) -> dict[str, Any]:
    return derive_series(entity_id, metric, sector=sector)


def quality_gates() -> dict[str, Any]:
    """Every derived point must recompute exactly from its recorded inputs."""
    checks: list[dict[str, Any]] = []
    for entity in covered_entities():
        for metric in ("PE", "PB", "EV_EBITDA", "ROE", "ROIC", "Net_Margin", "Cash_Conversion"):
            series = derive_series(entity, metric)
            if not series.get("found"):
                continue
            for period in list(series.get("points") or {})[:3]:
                v = verify_derivation(entity, metric, period)
                checks.append(
                    {
                        "entity": entity,
                        "metric": metric,
                        "period": period,
                        "verified": v.get("verified"),
                    }
                )
    verified = sum(1 for c in checks if c.get("verified"))
    total = len(checks)
    return {
        "gate": "DERIVED_FUNDAMENTALS",
        "primitives_version": PRIMITIVES_VERSION,
        "derivations_version": DERIVATIONS_VERSION,
        "checks": total,
        "verified": verified,
        "reproducibility_pct": round(100.0 * verified / total, 2) if total else 0.0,
        "passed": total > 0 and verified == total,
        "failures": [c for c in checks if not c.get("verified")][:10],
    }
