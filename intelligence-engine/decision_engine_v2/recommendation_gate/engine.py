"""Recommendation gate — readiness statuses only; never force buy/hold/sell."""

from __future__ import annotations

from typing import Any

from decision_engine_v2.schema import RECOMMENDATION_STATUSES


def apply_gate(
    *,
    evidence: dict[str, Any],
    conflicts: dict[str, Any],
    uncertainty: dict[str, Any],
    confidence: dict[str, Any],
    inputs: dict[str, Any],
    constitution: dict[str, Any],
) -> dict[str, Any]:
    summary = inputs.get("stack_summary") or {}
    layers = inputs.get("layers") or {}
    coverage = float(evidence.get("coverage") or 0)
    conf = float(confidence.get("confidence") or 0)
    conflict_n = int(conflicts.get("conflict_count") or 0)
    dominant_u = uncertainty.get("dominant")
    net = summary.get("portfolio_net_effect") or (
        (layers.get("portfolio_intelligence") or {}).get("impact") or {}
    ).get("net_portfolio_effect")

    status = "recommendation_ready"
    reasons: list[str] = []

    if coverage < 0.55:
        status = "evidence_insufficient"
        reasons.append("Evidence coverage below institutional threshold")
    elif not constitution.get("constitutional"):
        status = "further_research_required"
        reasons.append("Constitutional chain incomplete")
    elif net and str(net).lower() in {"weakens", "negative", "dilutive", "unsuitable"}:
        status = "portfolio_unsuitable"
        reasons.append(f"Portfolio context signals {net}")
    elif conflict_n >= 2 or dominant_u == "conflicting_evidence":
        status = "committee_review_required"
        reasons.append("Material conflicts require committee resolution")
    elif conf < 0.55 or dominant_u in {"known_unknown", "weak_evidence"}:
        status = "further_research_required"
        reasons.append("Confidence / uncertainty requires deeper research")
    elif conf < 0.7:
        status = "monitoring_required"
        reasons.append("Decision actionable only with active monitoring plan")
    else:
        reasons.append("Inputs sufficient for constitutional institutional judgement")

    assert status in RECOMMENDATION_STATUSES
    return {
        "status": status,
        "reasons": reasons,
        "allowed_statuses": list(RECOMMENDATION_STATUSES),
        "forced_buy_hold_sell": False,
        "never_force_trade": True,
        "policy_governed": True,
        "rule": "Recommendation status remains governed by policy — IDE V2 never forces Buy/Hold/Sell",
    }
