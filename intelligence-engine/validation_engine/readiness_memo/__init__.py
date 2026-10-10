"""Investment Research Readiness Memo — operational judgement before research."""

from __future__ import annotations

from typing import Any


def build_readiness_memo(
    *,
    question: str,
    readiness_state: str,
    overall_readiness: float,
    components: dict[str, dict[str, Any]],
    warnings: list[str],
    routing_status: dict[str, Any],
    evidence_status: dict[str, Any],
    entity_status: dict[str, Any],
    expected_runtime_s: float | None = None,
) -> dict[str, Any]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []

    if (components.get("entity") or {}).get("score", 0) >= 0.85:
        strengths.append("Clear entity")
    if (components.get("intent") or {}).get("score", 0) >= 0.85:
        strengths.append("Clear objective")
    if evidence_status.get("filings_exist"):
        strengths.append("Strong filing coverage")
    if evidence_status.get("peers_available"):
        strengths.append("Good peer data")
    if evidence_status.get("macro_available"):
        strengths.append("Complete macro context")
    if (components.get("blueprint") or {}).get("score", 0) >= 0.85:
        strengths.append("Publication blueprint ready")
    if (components.get("routing") or {}).get("score", 0) >= 0.85:
        strengths.append("Analyst/layer routing complete")

    for w in warnings:
        if "transcript" in w.lower() or "incomplete" in w.lower() or "pending" in w.lower():
            weaknesses.append(w)
        else:
            risks.append(w)
    for issue in evidence_status.get("missing") or []:
        weaknesses.append(f"Missing evidence: {issue}")
    if entity_status.get("entity_state") in {"historical", "merged", "delisted"}:
        risks.append(f"Entity state is {entity_status.get('entity_state')}")

    expected_confidence = round(min(0.99, overall_readiness * 0.95 + 0.02), 4)
    runtime = expected_runtime_s
    if runtime is None:
        # heuristic from readiness/complexity
        runtime = round(2.0 + (1.0 - overall_readiness) * 4.0 + 0.3 * len(routing_status.get("recommended_analysts") or []), 2)

    return {
        "title": "Research Readiness Memo",
        "question": question,
        "status": readiness_state,
        "readiness": round(overall_readiness, 4),
        "readiness_pct": int(round(overall_readiness * 100)),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "recommended_analysts": list(routing_status.get("recommended_analysts") or []),
        "suppressed": list(routing_status.get("suppressed") or []),
        "expected_confidence": expected_confidence,
        "expected_runtime_seconds": runtime,
        "entity": (entity_status.get("canonical_entity") or {}).get("canonical_name")
        or entity_status.get("ticker"),
        "evidence_can_answer": bool(evidence_status.get("can_answer")),
    }
