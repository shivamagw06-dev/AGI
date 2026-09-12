"""IDEB quality audit."""

from __future__ import annotations

from typing import Any

from debate_engine.schema import (
    MIN_CHALLENGED_ASSUMPTIONS,
    MIN_EVIDENCE_CONFLICTS,
    MIN_MINORITY_OPINIONS,
    MIN_SUPPORTING_POSITIONS,
    MIN_UNRESOLVED_QUESTIONS,
)


def audit_debate(debate: dict[str, Any]) -> dict[str, Any]:
    positions = debate.get("analyst_positions") or []
    supporting = sum(
        1 for p in positions if p.get("position") in ("Strong Support", "Support")
    )
    assumptions = len(debate.get("assumption_conflicts") or [])
    evidence = len(debate.get("evidence_conflicts") or [])
    minority = len(debate.get("minority_report") or [])
    open_questions = len(debate.get("open_questions") or [])
    tournament = debate.get("challenge_tournament") or {}
    scorecard = debate.get("debate_scorecard") or {}
    checks = {
        "min_supporting_positions": supporting >= MIN_SUPPORTING_POSITIONS,
        "min_challenged_assumptions": assumptions >= MIN_CHALLENGED_ASSUMPTIONS,
        "min_evidence_conflicts": evidence >= MIN_EVIDENCE_CONFLICTS,
        "min_minority_opinions": minority >= MIN_MINORITY_OPINIONS,
        "min_unresolved_questions": open_questions >= MIN_UNRESOLVED_QUESTIONS,
        "challenge_tournament_complete": bool(tournament.get("completed")),
        "minority_preserved": all(m.get("preserved") for m in (debate.get("minority_report") or [])),
        "scorecard_complete": len((scorecard.get("metrics") or {})) >= 6,
        "moderator_complete": bool((debate.get("moderator") or {}).get("moderator_conclusion")),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "counts": {
            "supporting_positions": supporting,
            "challenged_assumptions": assumptions,
            "evidence_conflicts": evidence,
            "minority_opinions": minority,
            "unresolved_questions": open_questions,
            "tournament_rounds": tournament.get("round_count", 0),
        },
        "targets": {
            "supporting_positions": MIN_SUPPORTING_POSITIONS,
            "challenged_assumptions": MIN_CHALLENGED_ASSUMPTIONS,
            "evidence_conflicts": MIN_EVIDENCE_CONFLICTS,
            "minority_opinions": MIN_MINORITY_OPINIONS,
            "unresolved_questions": MIN_UNRESOLVED_QUESTIONS,
        },
    }
