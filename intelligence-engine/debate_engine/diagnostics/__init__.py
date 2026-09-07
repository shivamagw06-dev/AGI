"""IDEB diagnostics — explain conflict detection and consensus."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from debate_engine.production import generate_for_question

    row = generate_for_question(question, body)
    debate = row.get("debate") or {}
    return {
        "ok": True,
        "question": row.get("question"),
        "thesis": debate.get("investment_thesis"),
        "positions": debate.get("analyst_positions"),
        "agreement_count": (debate.get("agreement") or {}).get("agreement_count"),
        "disagreement_count": (debate.get("disagreement") or {}).get("disagreement_count"),
        "evidence_conflict_count": len(debate.get("evidence_conflicts") or []),
        "assumption_conflict_count": len(debate.get("assumption_conflicts") or []),
        "minority_count": len(debate.get("minority_report") or []),
        "consensus": debate.get("consensus"),
        "tournament": {
            "round_count": (debate.get("challenge_tournament") or {}).get("round_count"),
            "revision_count": (debate.get("challenge_tournament") or {}).get("revision_count"),
        },
        "scorecard": debate.get("debate_scorecard"),
        "audit": debate.get("audit"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
        "not_another_committee": True,
    }
