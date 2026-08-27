"""IRQ diagnostics — explain research-question coverage and quality."""

from __future__ import annotations

from typing import Any

from research_questions.quality_rules import coverage_report


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from research_questions.production import generate_for_question

    row = generate_for_question(question, body)
    blocks = row.get("hypothesis_question_sets") or []
    return {
        "ok": True,
        "question": row.get("question"),
        "hypothesis_count": row.get("hypothesis_count"),
        "research_question_count": row.get("research_question_count"),
        "coverage": row.get("coverage"),
        "sets": [
            {
                "hypothesis_id": b.get("hypothesis_id"),
                "hypothesis": b.get("hypothesis"),
                "question_count": b.get("question_count"),
                "coverage": coverage_report(list(b.get("research_questions") or [])),
                "proof_chain": (b.get("question_tree") or {}).get("proof_chain"),
                "top_impact": [
                    {
                        "id": q.get("id"),
                        "question": q.get("question"),
                        "decision_impact": q.get("decision_impact"),
                        "priority": q.get("priority"),
                        "analyst_owner": q.get("analyst_owner"),
                    }
                    for q in sorted(
                        b.get("research_questions") or [],
                        key=lambda x: -int(x.get("decision_impact") or 0),
                    )[:5]
                ],
            }
            for b in blocks
        ],
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }
