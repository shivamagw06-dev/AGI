"""Regression risk assessment for a proposed patch (never auto-applies)."""

from __future__ import annotations

from typing import Any


def assess_risk(cluster: dict[str, Any]) -> dict[str, Any]:
    cause = str(cluster.get("root_cause") or "")
    sector = str(cluster.get("sector") or "generic")
    count = int(cluster.get("count") or 0)

    if cause in {"future_leakage", "fabricated_or_invented", "quality_gate_fail"}:
        level = "high"
        rationale = "Integrity / safety gate — patches must not loosen PIT filters"
    elif cause == "framework_mismatch" and sector in {"banks", "nbfc", "insurance"}:
        level = "medium"
        rationale = "Banking forbidden-list (no EV/EBITDA) must remain intact"
    elif cause == "framework_mismatch":
        level = "medium"
        rationale = "Sector composition changes can perturb adjacent categories"
    elif cause == "intent_mismatch":
        level = "medium"
        rationale = "Routing changes can cascade into framework/playbook selection"
    else:
        level = "low"
        rationale = "Localised cluster with limited cascade surface"

    if count >= 20 and level == "low":
        level = "medium"

    return {
        "risk": level,
        "rationale": rationale,
        "must_not_regress": [
            "cio_frozen_25 soft pass_pct",
            "banks forbid FW_EV_EBITDA",
            "replay available_from <= as_of",
            "IEL institutional_1000 pass_pct vs baseline",
        ],
    }
