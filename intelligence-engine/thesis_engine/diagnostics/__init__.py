"""ITCE diagnostics — explain thesis construction."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from thesis_engine.production import generate_for_question

    row = generate_for_question(question, body)
    thesis = row.get("thesis") or {}
    return {
        "ok": True,
        "question": row.get("question"),
        "core_thesis": (thesis.get("core_thesis") or {}).get("statement"),
        "status": thesis.get("status"),
        "conviction": thesis.get("conviction"),
        "pillars": [
            {
                "pillar": p.get("pillar"),
                "strength": p.get("strength"),
                "confidence": p.get("confidence"),
                "verdict": p.get("verdict"),
                "belief_ids": p.get("belief_ids"),
            }
            for p in (thesis.get("supporting_pillars") or [])
        ],
        "contradictions": {
            "major_count": (thesis.get("contradictions") or {}).get("major_count"),
            "outstanding_questions": (thesis.get("contradictions") or {}).get("outstanding_questions"),
        },
        "catalyst_summary": thesis.get("catalyst_summary"),
        "timeline": (thesis.get("timeline") or {}).get("horizons"),
        "audit": thesis.get("audit"),
        "dependency_propagation": (thesis.get("dependency_graph") or {}).get("propagation"),
        "pillar_interactions": (thesis.get("pillar_interaction_matrix") or {}).get("edges"),
        "stability": thesis.get("stability"),
        "quality": thesis.get("quality"),
        "pressure_gauge": thesis.get("pressure_gauge"),
        "evolution": thesis.get("evolution"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }
