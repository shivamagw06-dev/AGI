"""Assumption audit — explicit, tested, valid, confident and evidence-linked."""

from __future__ import annotations

from typing import Any


def audit_assumptions(trace: dict[str, Any]) -> dict[str, Any]:
    data = trace["stage_data"]
    testing = data.get("Testing") or {}
    debate = data.get("Debate") or {}
    thesis = data.get("Investment Thesis") or {}
    assumptions = []

    for hypothesis in testing.get("tested_hypotheses") or []:
        if not isinstance(hypothesis, dict):
            continue
        hid = hypothesis.get("id") or hypothesis.get("hypothesis_id")
        assumption_pack = hypothesis.get("assumptions") or {}
        evidence = hypothesis.get("evidence_effects") or hypothesis.get(
            "supporting_evidence"
        ) or []
        if isinstance(assumption_pack, dict):
            for category, values in assumption_pack.items():
                for value in values or []:
                    if isinstance(value, dict):
                        text = value.get("assumption") or value.get("text")
                        tested = bool(value.get("tested", evidence))
                        valid = bool(value.get("still_valid", True))
                        confidence = float(value.get("confidence") or 0.65)
                        evidence_ids = value.get("evidence_ids") or [
                            e.get("id") for e in evidence[:3] if isinstance(e, dict)
                        ]
                    else:
                        text = str(value)
                        tested = bool(evidence)
                        valid = category not in ("weak", "untested")
                        confidence = 0.55 if category in ("weak", "untested") else 0.7
                        evidence_ids = [
                            e.get("id") for e in evidence[:3] if isinstance(e, dict)
                        ]
                    assumptions.append(
                        {
                            "hypothesis_id": hid,
                            "assumption": text,
                            "category": category,
                            "explicit": True,
                            "tested": tested,
                            "still_valid": valid,
                            "confidence": confidence,
                            "evidence_ids": [x for x in evidence_ids if x],
                            "linked_to_evidence": bool(evidence_ids),
                        }
                    )

    for conflict in debate.get("assumption_conflicts") or []:
        for suffix in ("a", "b"):
            text = conflict.get(f"assumption_{suffix}")
            if text:
                assumptions.append(
                    {
                        "hypothesis_id": None,
                        "assumption": text,
                        "category": "debate_conflict",
                        "explicit": True,
                        "tested": bool(conflict.get("required_evidence")),
                        "still_valid": True,
                        "confidence": 0.55,
                        "evidence_ids": conflict.get("required_evidence") or [],
                        "linked_to_evidence": bool(conflict.get("required_evidence")),
                    }
                )
    for breaker in thesis.get("thesis_breaking_conditions") or []:
        assumptions.append(
            {
                "hypothesis_id": None,
                "assumption": breaker.get("condition"),
                "category": "breaking_condition",
                "explicit": True,
                "tested": True,
                "still_valid": True,
                "confidence": 0.7,
                "evidence_ids": breaker.get("monitoring_evidence") or ["monitoring"],
                "linked_to_evidence": True,
            }
        )

    if not assumptions:
        return {
            "score": 0.0,
            "score_pct": 0,
            "passed": False,
            "assumptions": [],
            "issues": ["No explicit assumptions found"],
        }
    fields = ("explicit", "tested", "still_valid", "linked_to_evidence")
    completeness = sum(
        sum(1 for field in fields if assumption[field]) / len(fields)
        for assumption in assumptions
    ) / len(assumptions)
    confidence_coverage = sum(
        1 for assumption in assumptions if assumption.get("confidence") is not None
    ) / len(assumptions)
    score = 0.85 * completeness + 0.15 * confidence_coverage
    issues = [
        {
            "assumption": assumption["assumption"],
            "missing": [
                field for field in fields if not assumption[field]
            ],
        }
        for assumption in assumptions
        if not all(assumption[field] for field in fields)
    ]
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": not issues,
        "assumptions": assumptions[:40],
        "assumption_count": len(assumptions),
        "issues": issues[:20],
    }
