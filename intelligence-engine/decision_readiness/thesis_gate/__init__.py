"""Reasoning/thesis gate — verify the full reasoning chain is complete and consistent."""

from __future__ import annotations

from typing import Any


def evaluate_reasoning(
    thesis: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    hypothesis_testing = payload.get("hypothesis_testing") or {}
    belief_engine = payload.get("belief_engine") or {}
    falsification = (
        payload.get("falsification_engine")
        or payload.get("falsification")
        or {}
    )
    checks = {
        "hypotheses_tested": bool(hypothesis_testing)
        or bool(thesis.get("supporting_pillars")),
        "falsification_complete": bool(falsification)
        or bool(payload.get("falsification_complete")),
        "belief_updated": bool(belief_engine)
        or bool(thesis.get("conviction")),
        "assumptions_explicit": bool(thesis.get("thesis_breaking_conditions"))
        or bool((thesis.get("contradictions") or {}).get("outstanding_questions")),
        "logic_consistent": bool((thesis.get("audit") or {}).get("passed", True)),
        "thesis_constructed": bool(
            (thesis.get("core_thesis") or {}).get("statement")
            if isinstance(thesis.get("core_thesis"), dict)
            else thesis.get("core_thesis")
        ),
    }
    weights = {
        "hypotheses_tested": 0.2,
        "falsification_complete": 0.2,
        "belief_updated": 0.2,
        "assumptions_explicit": 0.15,
        "logic_consistent": 0.15,
        "thesis_constructed": 0.1,
    }
    score = sum(weights[k] for k, passed in checks.items() if passed)
    return {
        "dimension": "Reasoning",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()),
        "checks": checks,
        "falsification_cycles": 1 if checks["falsification_complete"] else 0,
        "strengths": [
            label
            for key, label in {
                "hypotheses_tested": "Hypotheses tested",
                "falsification_complete": "Falsification cycle complete",
                "belief_updated": "Beliefs updated",
                "assumptions_explicit": "Assumptions explicit",
                "logic_consistent": "Logic consistent",
                "thesis_constructed": "Thesis constructed",
            }.items()
            if checks[key]
        ],
        "weaknesses": [
            label
            for key, label in {
                "hypotheses_tested": "Hypotheses require testing",
                "falsification_complete": "Falsification incomplete",
                "belief_updated": "Belief update missing",
                "assumptions_explicit": "Assumptions not explicit",
                "logic_consistent": "Logical inconsistency detected",
                "thesis_constructed": "Thesis missing",
            }.items()
            if not checks[key]
        ],
    }
