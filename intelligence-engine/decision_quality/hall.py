"""Decision Hall of Fame / Hall of Shame — searchable institutional memory.

Classifies decisions for pattern analysis. Never changes reasoning.
"""

from __future__ import annotations

from typing import Any

from decision_quality import store as idq_store
from decision_quality.metrics.compute import compute_decision_metrics
from decision_quality.schema import HALL_CATEGORIES


def classify_decision(decision: dict[str, Any]) -> dict[str, Any]:
    og = decision.get("outcome_graph") or {}
    if not og.get("available"):
        return {
            "decision_id": decision.get("decision_id"),
            "category": None,
            "insufficient": True,
            "reason": "outcome_unavailable",
            "fabricated": False,
            "hall": None,
        }

    m = compute_decision_metrics(decision)
    metrics = m.get("metrics") or {}
    evidence_q = float(metrics.get("evidence_quality") or 0)
    calibration = float(metrics.get("confidence_calibration") or 0)
    correct = bool(decision.get("prediction_correct"))
    modes = set(decision.get("failure_modes") or [])

    if not correct:
        if "missing_evidence" in modes or evidence_q < 50:
            category = "incorrect_missing_evidence"
        elif "framework_selection" in modes:
            category = "incorrect_framework_selection"
        elif "macro_assumption" in modes:
            category = "incorrect_macro_assumption"
        elif "portfolio_construction" in modes:
            category = "incorrect_portfolio_construction"
        else:
            category = "weak"
        hall = "shame"
    else:
        if evidence_q >= 88 and calibration >= 75:
            category = "exceptional"
        elif evidence_q >= 75 and calibration >= 60:
            category = "good"
        elif evidence_q >= 55:
            category = "average"
        else:
            category = "weak"
        hall = "fame" if category in {"exceptional", "good"} else "neutral"

    assert category in HALL_CATEGORIES or category is None
    return {
        "decision_id": decision.get("decision_id"),
        "entity": decision.get("entity"),
        "sector": decision.get("sector"),
        "macro_regime": decision.get("macro_regime"),
        "primary_framework": decision.get("primary_framework"),
        "category": category,
        "hall": hall,
        "evidence_quality": evidence_q,
        "confidence_calibration": calibration,
        "prediction_correct": correct,
        "failure_modes": sorted(modes),
        "why": _why(category, modes, evidence_q, calibration, correct),
        "insufficient": False,
        "fabricated": False,
        "searchable_institutional_memory": True,
    }


def _why(category: str, modes: set[str], evidence_q: float, calibration: float, correct: bool) -> str:
    if category == "exceptional":
        return "High-quality evidence, correct outcome, well-calibrated confidence"
    if category == "good":
        return "Correct outcome with solid evidence and acceptable calibration"
    if category == "average":
        return "Correct but middling evidence/calibration"
    if category == "weak":
        return "Weak process quality even if/when outcome known"
    if category == "incorrect_missing_evidence":
        return "Incorrect due to missing or thin evidence"
    if category == "incorrect_framework_selection":
        return "Incorrect due to framework selection"
    if category == "incorrect_macro_assumption":
        return "Incorrect due to macro assumption"
    if category == "incorrect_portfolio_construction":
        return "Incorrect due to portfolio construction"
    return "Unclassified"


def build_hall(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [classify_decision(d) for d in decisions]
    fame = [e for e in entries if e.get("hall") == "fame"]
    shame = [e for e in entries if e.get("hall") == "shame"]
    by_category: dict[str, list[dict[str, Any]]] = {c: [] for c in HALL_CATEGORIES}
    for e in entries:
        cat = e.get("category")
        if cat in by_category:
            by_category[cat].append(e)

    payload = {
        "hall_of_fame": fame,
        "hall_of_shame": shame,
        "by_category": {k: v for k, v in by_category.items() if v},
        "counts": {
            "fame": len(fame),
            "shame": len(shame),
            "classified": sum(1 for e in entries if e.get("category")),
            "insufficient": sum(1 for e in entries if e.get("insufficient")),
        },
        "categories": list(HALL_CATEGORIES),
        "observability_only": True,
        "fabricated": False,
    }
    idq_store.put_hall(payload)
    return payload


def search_hall(*, category: str | None = None, hall: str | None = None) -> dict[str, Any]:
    index = idq_store.get_hall() or {}
    if not index:
        return {"found": False, "reason": "hall_not_built", "insufficient": True, "fabricated": False}
    rows: list[dict[str, Any]] = []
    if hall == "fame":
        rows = list(index.get("hall_of_fame") or [])
    elif hall == "shame":
        rows = list(index.get("hall_of_shame") or [])
    else:
        for bucket in (index.get("hall_of_fame") or []), (index.get("hall_of_shame") or []):
            rows.extend(bucket)
        # include neutrals from by_category
        for cat_rows in (index.get("by_category") or {}).values():
            for e in cat_rows:
                if e not in rows:
                    rows.append(e)
    if category:
        rows = [r for r in rows if r.get("category") == category]
    return {
        "found": True,
        "n": len(rows),
        "results": rows,
        "fabricated": False,
    }
