"""Module 6 — Review Committee.

Reviews decisions (does not make them). Structured quality assessment.
"""

from __future__ import annotations

from typing import Any

REVIEW_VERSION = "review-committee-v1.0.0"


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def convene_review(
    lifecycle: dict[str, Any],
    evaluation: dict[str, Any],
    attribution: dict[str, Any],
    market: dict[str, Any],
) -> dict[str, Any]:
    score = float(evaluation.get("score") or 0.0)
    wrong = set(attribution.get("wrong") or [])
    correct = set(attribution.get("correct") or [])

    evidence_ok = "evidence" not in wrong and bool(lifecycle.get("research_djg"))
    policy_ok = "policy" not in wrong
    scenario_ok = "scenario" not in wrong
    sizing_ok = "sizing" not in wrong
    valuation_ok = not any(w for w in wrong if "rel_val" in w or "hist_multiples" in w or w == "valuation")

    worked = sorted(correct)[:8]
    failed = sorted(wrong)[:8]

    research_q = 90.0 if evidence_ok and valuation_ok else 55.0 if evidence_ok else 35.0
    risk_q = 88.0 if sizing_ok and float(evaluation.get("downside_error") or 0) <= 0.08 else 50.0
    portfolio_q = 90.0 if policy_ok and sizing_ok else 45.0
    decision_q = score
    overall = round(0.35 * decision_q + 0.25 * research_q + 0.20 * risk_q + 0.20 * portfolio_q, 2)

    answers = {
        "what_worked": worked or ["traceability"],
        "what_failed": failed or ([] if score >= 70 else ["return_assumption"]),
        "evidence_sufficient": evidence_ok,
        "policy_correct": policy_ok,
        "scenario_reasonable": scenario_ok,
        "sizing_appropriate": sizing_ok,
    }

    return {
        "review_version": REVIEW_VERSION,
        "questions": answers,
        "decision_quality": {"score": round(decision_q, 2), "grade": _grade(decision_q)},
        "research_quality": {"score": round(research_q, 2), "grade": _grade(research_q)},
        "risk_quality": {"score": round(risk_q, 2), "grade": _grade(risk_q)},
        "portfolio_quality": {"score": round(portfolio_q, 2), "grade": _grade(portfolio_q)},
        "overall_quality": {"score": overall, "grade": _grade(overall)},
        "alpha": market.get("alpha"),
        "primary_failure": attribution.get("primary_failure"),
        "can_learn_later": True,
        "learning_applied": False,
        "note": "Review only — no framework or policy updates (Phase 7).",
    }
