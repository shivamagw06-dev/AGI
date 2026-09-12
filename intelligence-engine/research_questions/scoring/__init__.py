"""Decision impact scoring — focus analyst effort on material questions."""

from __future__ import annotations

from typing import Any

_PRIORITY_IMPACT = {
    "Critical": 10,
    "Important": 8,
    "Supporting": 5,
    "Optional": 2,
}


def score_decision_impact(question: dict[str, Any]) -> int:
    if question.get("decision_impact") is not None:
        return max(1, min(10, int(question["decision_impact"])))
    return _PRIORITY_IMPACT.get(str(question.get("priority") or "Supporting"), 5)


def attach_scores(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for q in questions:
        impact = score_decision_impact(q)
        # Confidence starts as prior belief that the question is answerable with available evidence
        base_conf = 0.72 if impact >= 8 else 0.64 if impact >= 5 else 0.55
        if len(q.get("required_evidence") or []) >= 2:
            base_conf = min(0.9, base_conf + 0.05)
        out.append(
            {
                **q,
                "decision_impact": impact,
                "decision_impact_label": f"{impact}/10",
                "confidence": round(float(q.get("confidence") or base_conf), 4),
            }
        )
    return out


def impact_summary(questions: list[dict[str, Any]]) -> dict[str, Any]:
    if not questions:
        return {"mean_impact": 0.0, "critical_count": 0, "high_impact_share": 0.0}
    impacts = [int(q.get("decision_impact") or 0) for q in questions]
    high = sum(1 for i in impacts if i >= 8)
    return {
        "mean_impact": round(sum(impacts) / len(impacts), 2),
        "critical_count": sum(1 for q in questions if q.get("priority") == "Critical"),
        "high_impact_share": round(high / len(impacts), 4),
        "top_questions": [
            {"id": q.get("id"), "question": q.get("question"), "decision_impact": q.get("decision_impact")}
            for q in sorted(questions, key=lambda x: -int(x.get("decision_impact") or 0))[:5]
        ],
    }
