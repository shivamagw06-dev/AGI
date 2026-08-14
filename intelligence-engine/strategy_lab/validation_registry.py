"""Authoritative lifecycle and health decisions for Strategy Lab.

Strategies may publish mathematical research outputs, but they cannot promote
themselves. This module turns explicit validation evidence into the only
governance decision consumed by Strategy Lab.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

REGISTRY_VERSION = "strategy-validation-registry-v2.0.0"

LIFECYCLES = (
    "EXPERIMENTAL",
    "OPERATIONAL",
    "BACKTESTABLE",
    "RESEARCH_VALIDATED",
    "INVESTMENT_VALIDATED",
    "PRODUCTION_CANDIDATE",
    "PRODUCTION",
)
HEALTH_STATES = ("HEALTHY", "DEGRADED", "STALE", "SUSPENDED", "FAILED")
EVIDENCE_STATES = ("PASSED", "PARTIAL", "FAILED", "MISSING", "NOT_APPLICABLE")

GATES = (
    "implementation",
    "data_freshness",
    "data_completeness",
    "point_in_time",
    "corporate_actions",
    "backtest",
    "out_of_sample",
    "transaction_costs",
    "liquidity_capacity",
    "risk",
    "walk_forward_paper",
    "operational_controls",
)

REQUIRED_BY_LIFECYCLE = {
    "EXPERIMENTAL": (),
    "OPERATIONAL": ("implementation", "data_freshness", "data_completeness"),
    "BACKTESTABLE": ("implementation", "data_freshness", "data_completeness", "point_in_time", "corporate_actions"),
    "RESEARCH_VALIDATED": (
        "implementation", "data_freshness", "data_completeness", "point_in_time", "corporate_actions",
        "backtest", "out_of_sample", "transaction_costs", "liquidity_capacity",
    ),
    "INVESTMENT_VALIDATED": (
        "implementation", "data_freshness", "data_completeness", "point_in_time", "corporate_actions",
        "backtest", "out_of_sample", "transaction_costs", "liquidity_capacity", "risk", "walk_forward_paper",
    ),
    "PRODUCTION_CANDIDATE": GATES,
    "PRODUCTION": GATES,
}


def _state(value: Any) -> str:
    state = str(value or "MISSING").upper()
    return state if state in EVIDENCE_STATES else "MISSING"


def normalise_evidence(evidence: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    source = evidence or {}
    normalised: dict[str, dict[str, Any]] = {}
    for gate in GATES:
        raw = source.get(gate, {})
        if isinstance(raw, str):
            raw = {"status": raw}
        normalised[gate] = {
            "status": _state(raw.get("status")),
            "observed_at": raw.get("observed_at"),
            "source": raw.get("source"),
            "receipt_id": raw.get("receipt_id"),
            "detail": raw.get("detail"),
        }
    return normalised


def highest_supported_lifecycle(evidence: dict[str, dict[str, Any]]) -> str:
    supported = "EXPERIMENTAL"
    for lifecycle in LIFECYCLES[1:]:
        required = REQUIRED_BY_LIFECYCLE[lifecycle]
        if all(evidence[gate]["status"] == "PASSED" for gate in required):
            supported = lifecycle
        else:
            break
    return supported


def evaluate(
    strategy_id: str,
    *,
    requested_lifecycle: str = "EXPERIMENTAL",
    evidence: dict[str, Any] | None = None,
    health: str = "HEALTHY",
    health_reason: str | None = None,
    allowed_use: str = "Research only",
) -> dict[str, Any]:
    requested = str(requested_lifecycle or "EXPERIMENTAL").upper()
    if requested not in LIFECYCLES:
        requested = "EXPERIMENTAL"
    current_health = str(health or "FAILED").upper()
    if current_health not in HEALTH_STATES:
        current_health = "FAILED"

    gates = normalise_evidence(evidence)
    supported = highest_supported_lifecycle(gates)
    effective_rank = min(LIFECYCLES.index(requested), LIFECYCLES.index(supported))
    effective = LIFECYCLES[effective_rank]
    required = REQUIRED_BY_LIFECYCLE[requested]
    failed = [gate for gate in required if gates[gate]["status"] == "FAILED"]
    missing = [gate for gate in required if gates[gate]["status"] in {"MISSING", "PARTIAL"}]

    health_blocks = current_health in {"STALE", "SUSPENDED", "FAILED"}
    execution_allowed = effective == "PRODUCTION" and current_health == "HEALTHY" and not failed and not missing
    demoted = effective != requested or health_blocks
    return {
        "strategy_id": strategy_id,
        "registry_version": REGISTRY_VERSION,
        "authority": "VALIDATION_REGISTRY",
        "requested_lifecycle": requested,
        "supported_lifecycle": supported,
        "lifecycle": effective,
        "health": current_health,
        "health_reason": health_reason or "No active reliability breach detected.",
        "allowed_use": allowed_use,
        "execution": "ALLOWED" if execution_allowed else "BLOCKED",
        "historical_alpha_claims_allowed": effective in LIFECYCLES[3:] and not health_blocks,
        "automatic_demotion": demoted,
        "failed_gates": failed,
        "missing_gates": missing,
        "evidence": gates,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_authority": "VALIDATION_REGISTRY_ONLY",
    }

