"""Weighted institutional decision-readiness engine and heat map."""

from __future__ import annotations

from typing import Any

from decision_readiness.schema import READINESS_STATES, READINESS_WEIGHTS


def classify_readiness(
    score: float,
    gates: dict[str, dict[str, Any]],
) -> str:
    evidence = gates["Evidence"]
    reasoning = gates["Reasoning"]
    debate = gates["Debate"]
    policy = gates["Policy"]
    monitoring = gates["Monitoring"]
    if int(policy.get("critical_violation_count") or 0) > 0:
        return "NOT READY"
    if evidence["score"] < 0.55 or reasoning["score"] < 0.5:
        return "NOT READY"
    if (
        score >= 0.86
        and evidence.get("coverage_pct", 0) >= 90
        and reasoning.get("falsification_cycles", 0) >= 1
        and debate.get("minority_reviewed")
        and monitoring.get("active_trigger_count", 0) >= 3
        and debate["score"] >= 0.72
    ):
        return "READY"
    if (
        score >= 0.70
        and evidence["score"] >= 0.75
        and debate["score"] >= 0.55
        and policy.get("passed")
        and monitoring["score"] >= 0.75
    ):
        return "READY WITH CONDITIONS"
    if score >= 0.52:
        return "RESEARCH REQUIRED"
    return "NOT READY"


def aggregate_readiness(
    *,
    evidence: dict[str, Any],
    reasoning: dict[str, Any],
    debate: dict[str, Any],
    portfolio: dict[str, Any],
    monitoring: dict[str, Any],
    policy: dict[str, Any],
    confidence: dict[str, Any],
) -> dict[str, Any]:
    gates = {
        "Evidence": evidence,
        "Reasoning": reasoning,
        "Debate": debate,
        "Portfolio": portfolio,
        "Monitoring": monitoring,
        "Policy": policy,
        "Confidence": confidence,
    }
    score = sum(
        READINESS_WEIGHTS[name] * float(gates[name]["score"])
        for name in READINESS_WEIGHTS
    )
    score = round(max(0.0, min(1.0, score)), 4)
    status = classify_readiness(score, gates)
    assert status in READINESS_STATES
    heat_map = [
        {
            "dimension": name,
            "score": gate["score"],
            "score_pct": gate["score_pct"],
            "weight": READINESS_WEIGHTS.get(name),
            "weighted_contribution": (
                round(READINESS_WEIGHTS[name] * gate["score"], 4)
                if name in READINESS_WEIGHTS
                else None
            ),
            "passed": gate.get("passed"),
            "state": (
                "Strong"
                if gate["score"] >= 0.85
                else "Adequate"
                if gate["score"] >= 0.7
                else "Weak"
                if gate["score"] >= 0.5
                else "Blocked"
            ),
        }
        for name, gate in gates.items()
    ]
    strengths = []
    weaknesses = []
    for name, gate in gates.items():
        strengths.extend(
            [
                {"dimension": name, "factor": item}
                for item in (gate.get("strengths") or [])
                if item
            ]
        )
        weaknesses.extend(
            [
                {"dimension": name, "factor": item}
                for item in (gate.get("weaknesses") or [])
                if item
            ]
        )
        if gate["score"] >= 0.85:
            strengths.append(
                {"dimension": name, "factor": f"{name} readiness is strong"}
            )
        elif gate["score"] < 0.7:
            weaknesses.append(
                {
                    "dimension": name,
                    "factor": f"{name} readiness is below institutional threshold",
                }
            )

    return {
        "decision_status": status,
        "readiness_score": score,
        "readiness_score_pct": round(score * 100),
        "dimensions": gates,
        "decision_heat_map": heat_map,
        "weights": dict(READINESS_WEIGHTS),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "confidence": confidence["confidence"],
        "confidence_pct": confidence["confidence_pct"],
        "uncertainty": confidence["uncertainty"],
    }
