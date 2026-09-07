"""Canonical Reliability & Validation Registry.

Models may emit signals, but only this registry may describe lifecycle,
validation, allowed use, current health or execution eligibility.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

LIFECYCLE = (
    "experimental", "operational", "backtestable", "research_validated",
    "investment_validated", "production_candidate", "production",
)
HEALTH = ("healthy", "degraded", "stale", "suspended", "failed")
VALIDATION_VERSION = "agi-reliability-v1.0.0"

_BASE: dict[str, dict[str, Any]] = {
    "long_short_equity": {"name": "Long / Short Equity", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "equity_market_neutral": {"name": "Equity Market Neutral", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "statistical_arbitrage": {"name": "Statistical Arbitrage", "lifecycle": "experimental", "allowed_use": "Calculator and research"},
    "global_macro": {"name": "Global Macro", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "merger_arbitrage": {"name": "Merger Arbitrage", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "convertible_arbitrage": {"name": "Convertible Arbitrage", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "cta_trend": {"name": "CTA / Managed Futures", "lifecycle": "experimental", "allowed_use": "Research methodology"},
    "distressed": {"name": "Distressed & Special Situations", "lifecycle": "experimental", "allowed_use": "Research screening"},
    "value": {"name": "Value Scanner", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "quality": {"name": "Quality Scanner", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "growth": {"name": "Forward Earnings Growth", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "conviction": {"name": "Consensus Conviction", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "dividend": {"name": "Dividend / Income", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "alpha": {"name": "Alpha Opportunity", "lifecycle": "operational", "allowed_use": "Research prioritisation"},
    "pairs": {"name": "Valuation Pairs", "lifecycle": "experimental", "allowed_use": "Candidate generation"},
    "stress": {"name": "Stress / Distressed", "lifecycle": "experimental", "allowed_use": "Forensic research triage"},
    "live_alpha": {"name": "Live Alpha", "lifecycle": "operational", "allowed_use": "Tactical research confirmation"},
    "fie": {"name": "Forecast Intelligence Engine", "lifecycle": "operational", "allowed_use": "Scenario research"},
    "fle": {"name": "Forecast Learning Engine", "lifecycle": "operational", "allowed_use": "Governed outcome measurement"},
}


def _gates(lifecycle: str) -> dict[str, str]:
    rank = LIFECYCLE.index(lifecycle)
    return {
        "pit_data": "partial" if rank < 2 else "passed",
        "backtest": "not_completed" if rank < 3 else "passed",
        "out_of_sample": "not_available" if rank < 3 else "passed",
        "transaction_costs": "not_validated" if rank < 3 else "passed",
        "risk": "not_validated" if rank < 4 else "passed",
        "investment_validation": "no" if rank < 4 else "yes",
    }


def component(
    component_id: str,
    *,
    health: str = "healthy",
    health_reason: str = "No active reliability breach detected.",
    evidence: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    base = _BASE.get(component_id, {"name": component_id, "lifecycle": "experimental", "allowed_use": "Research only"})
    lifecycle = base["lifecycle"]
    health = health if health in HEALTH else "failed"
    execution_allowed = lifecycle == "production" and health == "healthy"
    return {
        "component_id": component_id,
        "name": base["name"],
        "lifecycle": lifecycle,
        "lifecycle_label": lifecycle.replace("_", " ").title(),
        "health": health,
        "health_reason": health_reason,
        "validation": _gates(lifecycle),
        "allowed_use": base["allowed_use"],
        "execution": "allowed" if execution_allowed else "blocked",
        "historical_performance_claims": lifecycle in {"research_validated", "investment_validated", "production_candidate", "production"},
        "validation_version": VALIDATION_VERSION,
        "last_validation": datetime.now(timezone.utc).date().isoformat(),
        "evidence": evidence or {},
        "promotion_authority": "reliability_registry",
        "automatic_demotion": True,
    }


def registry(overrides: Optional[dict[str, dict[str, Any]]] = None) -> dict[str, Any]:
    overrides = overrides or {}
    rows = [component(key, **overrides.get(key, {})) for key in _BASE]
    return {
        "ok": True,
        "authority": "reliability_registry",
        "validation_version": VALIDATION_VERSION,
        "lifecycle_order": list(LIFECYCLE),
        "health_states": list(HEALTH),
        "components": rows,
        "execution_allowed": sum(r["execution"] == "allowed" for r in rows),
        "policy": "Promotion requires registry evidence. Health failures automatically block execution and may demote production use.",
    }
