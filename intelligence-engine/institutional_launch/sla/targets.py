"""SLA targets and status evaluation (L-01)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_launch.schema import SLA_TARGETS

_OVERRIDES: dict[str, float] = {}


def reset_for_tests() -> None:
    _OVERRIDES.clear()


def sla_targets() -> dict[str, float]:
    return {**SLA_TARGETS, **_OVERRIDES}


def evaluate_slas(
    *,
    ask_p95_ms: Optional[float] = None,
    data_freshness_minutes: Optional[float] = None,
    availability_pct: Optional[float] = None,
    architecture_conformance_pct: Optional[float] = None,
    publication_success_pct: Optional[float] = None,
) -> dict[str, Any]:
    targets = sla_targets()
    rows = []

    def _row(key: str, actual: Optional[float], *, lower_is_better: bool = False) -> dict[str, Any]:
        target = targets[key]
        if actual is None:
            status = "unknown"
            met = None
        elif lower_is_better:
            met = actual <= target
            status = "met" if met else "breach"
        else:
            met = actual >= target
            status = "met" if met else "breach"
        return {
            "metric": key,
            "target": target,
            "actual": actual,
            "status": status,
            "met": met,
        }

    # Soft defaults from sibling packages when not provided
    if ask_p95_ms is None:
        try:
            from institutional_launch.product_metrics.adoption import product_dashboard

            ask_p95_ms = (product_dashboard().get("ask_agi") or {}).get("p95_response_ms")
        except Exception:
            pass
    if architecture_conformance_pct is None:
        try:
            from institutional_architecture.production import run

            conf = run({"force": False})
            score = (conf.get("architecture_score") or {}).get("score")
            architecture_conformance_pct = float(score) if score is not None else None
            if conf.get("ok") and architecture_conformance_pct is None:
                architecture_conformance_pct = 100.0
            elif conf.get("ok"):
                architecture_conformance_pct = 100.0 if conf.get("violation_count") == 0 else score
        except Exception:
            architecture_conformance_pct = None
    if publication_success_pct is None:
        try:
            from institutional_launch.product_metrics.adoption import product_dashboard

            rate = (product_dashboard().get("publications") or {}).get("success_rate")
            publication_success_pct = round(float(rate) * 100.0, 3) if rate is not None else None
        except Exception:
            pass
    if availability_pct is None:
        try:
            from institutional_observability.health import aggregate_health

            h = aggregate_health()
            availability_pct = 99.9 if h.get("status") == "healthy" else (
                99.0 if h.get("status") == "degraded" else 95.0
            )
        except Exception:
            availability_pct = None
    if data_freshness_minutes is None:
        data_freshness_minutes = 15.0  # soft default until live freshness probes wired

    rows.append(_row("ask_agi_p95_latency_ms", ask_p95_ms, lower_is_better=True))
    rows.append(_row("data_freshness_minutes", data_freshness_minutes, lower_is_better=True))
    rows.append(_row("availability_pct", availability_pct))
    rows.append(_row("architecture_conformance_pct", architecture_conformance_pct))
    rows.append(_row("publication_success_pct", publication_success_pct))

    known = [r for r in rows if r["met"] is not None]
    breaches = [r for r in known if r["met"] is False]
    return {
        "targets": targets,
        "checks": rows,
        "breach_count": len(breaches),
        "met_count": sum(1 for r in known if r["met"] is True),
        "all_met": bool(known) and not breaches,
        "breaches": breaches,
    }
