"""Institutional Decision Quality dashboard + north-star KPI."""

from __future__ import annotations

from typing import Any

from decision_quality import store as idq_store
from decision_quality.metrics.compute import compute_decision_metrics
from decision_quality.schema import IDQ_VERSION, NORTH_STAR_COMPONENTS


def _avg(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 2) if xs else 0.0


def institutional_decision_quality_coverage() -> dict[str, Any]:
    decisions = idq_store.all_decisions()
    scored_metrics = []
    for d in decisions:
        m = compute_decision_metrics(d)
        if not m.get("insufficient"):
            scored_metrics.append(m["metrics"])

    decision_accuracy = _avg([float(m["decision_accuracy"]) for m in scored_metrics])
    evidence_quality = _avg(
        [float(m["evidence_quality"]) for m in scored_metrics]
        or [float((d.get("evidence_pack") or {}).get("quality_score") or 0) for d in decisions]
    )
    framework_accuracy = _avg([float(m["framework_selection_accuracy"]) for m in scored_metrics])
    confidence_calibration = _avg([float(m["confidence_calibration"]) for m in scored_metrics])
    portfolio_quality = _avg([float(m["portfolio_quality"]) for m in scored_metrics])
    research_quality = _avg([float(m["research_quality"]) for m in scored_metrics])
    outcome_quality = _avg([float(m["outcome_accuracy"]) for m in scored_metrics])

    components = {
        "decision_accuracy": decision_accuracy,
        "evidence_quality": evidence_quality,
        "framework_accuracy": framework_accuracy,
        "confidence_calibration": confidence_calibration,
        "portfolio_quality": portfolio_quality,
        "research_quality": research_quality,
        "outcome_quality": outcome_quality,
    }
    # North star as 0-100 average of components
    coverage = _avg([components[k] for k in NORTH_STAR_COMPONENTS])

    fw = idq_store.get_scorecard("framework", "_index") or {}
    sector = idq_store.get_scorecard("sector", "_index") or {}
    macro = idq_store.get_scorecard("macro", "_index") or {}
    portfolio = idq_store.get_scorecard("portfolio", "aggregate") or {}
    calibration = idq_store.get_calibration("latest") or {}
    hall = idq_store.get_hall() or {}

    learning_success = 0.0
    learning_n = 0
    for d in decisions:
        lp = d.get("learning_proposal")
        if not lp:
            continue
        learning_n += 1
        if lp.get("status") in {"approved", "deployed"}:
            learning_success += 100.0
        else:
            learning_success += 50.0
    learning_success = round(learning_success / learning_n, 2) if learning_n else 0.0

    return {
        "north_star_kpi": "institutional_decision_quality",
        "coverage": coverage,
        "institutional_decision_quality": coverage,
        "components": components,
        "research_accuracy": research_quality,
        "portfolio_accuracy": portfolio.get("decision_accuracy") or portfolio_quality,
        "framework_accuracy": framework_accuracy,
        "sector_accuracy": _avg(
            [float(c.get("prediction_accuracy") or 0) for c in (sector.get("scorecards") or {}).values()]
        ),
        "macro_accuracy": _avg(
            [float(c.get("average_accuracy") or 0) for c in (macro.get("scorecards") or {}).values()]
        ),
        "evidence_quality": evidence_quality,
        "confidence_calibration": confidence_calibration,
        "outcome_accuracy": outcome_quality,
        "learning_success": learning_success,
        "counts": {
            "decisions": len(decisions),
            "with_outcome": len(scored_metrics),
            "framework_scorecards": fw.get("n", 0),
            "sector_scorecards": sector.get("n", 0),
            "macro_scorecards": macro.get("n", 0),
            "hall_fame": (hall.get("counts") or {}).get("fame", 0),
            "hall_shame": (hall.get("counts") or {}).get("shame", 0),
        },
        "calibration_overall": calibration.get("overall"),
        "idq_version": IDQ_VERSION,
        "observability_only": True,
        "never_reasons": True,
        "fabricated": False,
    }


def institutional_decision_quality_dashboard() -> dict[str, Any]:
    kpi = institutional_decision_quality_coverage()
    return {
        "dashboard": "institutional_decision_quality",
        "kpi": kpi,
        "status": "operational" if float(kpi.get("coverage") or 0) >= 50 else "building",
        "idq_version": IDQ_VERSION,
        "displays": [
            "Institutional Decision Quality",
            "Research Accuracy",
            "Portfolio Accuracy",
            "Framework Accuracy",
            "Sector Accuracy",
            "Macro Accuracy",
            "Evidence Quality",
            "Confidence Calibration",
            "Outcome Accuracy",
            "Learning Success",
            "Hall of Fame / Hall of Shame",
        ],
    }


decision_quality_dashboard = institutional_decision_quality_dashboard
