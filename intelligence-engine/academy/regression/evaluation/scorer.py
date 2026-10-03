"""IRS evaluation — reasoning / evidence / framework scores (not wording match)."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import GoldenAnswerRef, GoldenQuestion


def _hit_rate(blob: str, items: list[str]) -> float:
    if not items:
        return 1.0
    hits = sum(1 for i in items if i.lower() in blob)
    return hits / len(items)


def score_response(
    question: GoldenQuestion,
    answer_ref: GoldenAnswerRef,
    response_text: str,
    structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blob = f"{response_text}\n{structure or {}}".lower()
    evidence = round(100.0 * _hit_rate(blob, answer_ref.evidence_checklist), 2)
    framework = round(100.0 * _hit_rate(blob, answer_ref.framework_checklist), 2)
    concepts = round(100.0 * _hit_rate(blob, answer_ref.concept_checklist), 2)
    reasoning = round(100.0 * _hit_rate(blob, answer_ref.reasoning_checklist), 2)

    # Evidence quality dimensions (soft heuristics)
    evidence_dims = {
        "completeness": evidence,
        "freshness": 80.0 if any(k in blob for k in ("current", "trajectory", "cycle", "recent")) else 70.0,
        "relevance": (
            90.0
            if (not question.company)
            or ((question.company or "").split()[:1] and (question.company or "").split()[0].lower() in blob)
            else 75.0
        ),
        "diversity": 85.0 if blob.count(",") + blob.count(";") >= 2 else 70.0,
        "conflicts_handled": 85.0 if any(k in blob for k in ("however", "risk", "but", "conditional")) else 72.0,
        "missing_identified": 88.0 if any(k in blob for k in ("missing", "gap", "incomplete", "uncertain", "if")) else 70.0,
    }
    evidence_score = round(sum(evidence_dims.values()) / len(evidence_dims), 2)

    # Domain reasoning score blends checklists
    domain_score = round(0.4 * reasoning + 0.3 * evidence + 0.3 * framework, 2)

    must_not_hit = [m for m in answer_ref.must_not if m.lower() in blob]
    penalty = 8.0 * len(must_not_hit)
    overall = max(0.0, min(100.0, round(0.5 * domain_score + 0.25 * evidence_score + 0.25 * concepts - penalty, 2)))

    return {
        "question_id": question.question_id,
        "domain": question.domain,
        "analyst": question.analyst,
        "reasoning_score": reasoning,
        "evidence_score": evidence_score,
        "framework_score": framework,
        "concept_score": concepts,
        "domain_score": domain_score,
        "overall": overall,
        "evidence_dimensions": evidence_dims,
        "must_not_violations": must_not_hit,
        "coverage": {
            "evidence": evidence,
            "framework": framework,
            "concept": concepts,
            "reasoning": reasoning,
        },
    }
