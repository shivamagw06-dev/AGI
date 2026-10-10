"""Playbook confidence scoring — soft overlay only."""

from __future__ import annotations

from typing import Any


def score_playbook_confidence(
    *,
    playbook: dict[str, Any],
    checklist: dict[str, Any],
    match_score: int,
    gaps_coverage: float | int | None,
    framework_overlap: int,
) -> dict[str, Any]:
    rules = playbook.get("confidence_rules") or {}
    pct = 45
    reasons: list[str] = []

    # Match strength
    if match_score >= 50:
        pct += 25
        reasons.append("strong_cue_match")
    elif match_score >= 25:
        pct += 15
        reasons.append("moderate_match")
    else:
        pct += 5
        reasons.append("weak_match_fallback")

    if framework_overlap > 0:
        pct += min(framework_overlap * 4, 12)
        reasons.append("framework_alignment")

    cov = checklist.get("coverage_pct") or 0
    min_cov = float(rules.get("min_checklist_coverage") or 0.5) * 100
    if cov >= min_cov:
        pct += int(rules.get("boost_full_procedure") or 8)
        reasons.append("checklist_evidence_hints")
    else:
        pct -= int(rules.get("penalty_missing_evidence") or 10)
        reasons.append("checklist_thin_evidence")

    if gaps_coverage is not None:
        try:
            g = float(gaps_coverage)
            if g < 0.4:
                pct -= 8
                reasons.append("assembly_gaps")
            elif g >= 0.7:
                pct += 6
                reasons.append("assembly_coverage")
        except (TypeError, ValueError):
            pass

    pct = max(15, min(92, int(pct)))
    if pct >= 75:
        band = "high"
    elif pct >= 55:
        band = "medium"
    else:
        band = "low"

    return {
        "pct": pct,
        "band": band,
        "reasons": reasons,
        "match_score": match_score,
        "framework_overlap": framework_overlap,
        "checklist_coverage_pct": cov,
        "fabricated": False,
    }
