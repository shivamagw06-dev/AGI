"""Conflict engine — never hide disagreement."""

from __future__ import annotations

from typing import Any


def detect_conflicts(inputs: dict[str, Any], *, committee: dict[str, Any] | None = None) -> dict[str, Any]:
    layers = inputs.get("layers") or {}
    summary = inputs.get("stack_summary") or {}
    conflicts: list[dict[str, Any]] = []

    fie = layers.get("forecast_intelligence") or {}
    ilm = layers.get("institutional_memory") or {}
    pio = layers.get("portfolio_intelligence") or {}
    aci = layers.get("accounting_intelligence") or {}
    mii = layers.get("management_intelligence") or {}

    # Forecast vs learning
    if fie.get("most_likely") and ilm.get("thinking_improved") is False:
        conflicts.append(
            {
                "type": "forecast_conflict",
                "why": "Forward scenario outlook sits against incomplete institutional learning improvement",
                "layers": ["FIE", "ILM"],
            }
        )

    # Portfolio vs quality
    net = summary.get("portfolio_net_effect") or (pio.get("impact") or {}).get("net_portfolio_effect")
    if net and str(net).lower() in {"weakens", "negative", "dilutive"}:
        conflicts.append(
            {
                "type": "portfolio_conflict",
                "why": f"Portfolio net effect signals '{net}' against potential franchise thesis",
                "layers": ["PIO", "FIL/MII"],
            }
        )

    # Accounting vs management trust
    manip = summary.get("manipulation_risk") or aci.get("manipulation_risk")
    mii_conf = summary.get("management_confidence") or mii.get("confidence")
    if manip and str(manip).lower() in {"elevated", "high", "watch"} and mii_conf and float(mii_conf) >= 0.6:
        conflicts.append(
            {
                "type": "evidence_conflict",
                "why": "Management confidence elevated while accounting manipulation risk is under watch",
                "layers": ["MII", "ACI"],
            }
        )

    # Committee disagreement soft marker
    committee = committee or layers.get("investment_committee") or {}
    if committee.get("disagreements") or committee.get("minority_opinions") or committee.get("stage_2_conflicts"):
        conflicts.append(
            {
                "type": "committee_disagreement",
                "why": "Committee retains minority views or unresolved stage-2 conflicts",
                "layers": ["IC"],
            }
        )

    # Analyst disagreement placeholder when opinions diverge in soft pack
    if committee.get("disagreement_matrix") or committee.get("disagreements"):
        conflicts.append(
            {
                "type": "analyst_disagreement",
                "why": "Specialist desks disagree on stance or evidence priority",
                "layers": ["IAF"],
            }
        )

    # SSL opportunity cost vs FIE base
    ssl = layers.get("simulation_lab") or {}
    if ssl.get("opportunity_cost_analysed") and fie.get("most_likely"):
        # Not always a conflict — surface as informational tension when stress incomplete
        if ssl.get("stress_completed") is False:
            conflicts.append(
                {
                    "type": "forecast_conflict",
                    "why": "Simulation stress incomplete relative to active forecast scenario",
                    "layers": ["SSL", "FIE"],
                }
            )

    explained = [{**c, "explained": True, "hidden": False} for c in conflicts]
    return {
        "conflict_count": len(explained),
        "conflicts": explained,
        "matrix": {c["type"]: c["why"] for c in explained},
        "rule": "Never hide disagreement — every conflict is explained",
        "never_hide_disagreement": True,
    }
