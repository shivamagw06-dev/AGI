"""Execution policy — which stages run vs skipped_by_policy."""

from __future__ import annotations

from typing import Any


def execution_policy(
    *,
    intent: str,
    investment_recommendation: bool = False,
    has_entity: bool = False,
    question_type: str | None = None,
    concept_mode: bool = False,
    as_of: str | None = None,
) -> dict[str, Any]:
    # Track A — explanatory / education / historical-replay / concept paths
    # must not enter live valuation packaging.
    education = (
        intent
        in {
            "Education",
            "Explain",
            "HistoricalReplay",
            "Documents",
        }
        or question_type == "education"
        or (concept_mode and intent in {"Explain", "Education", "Unknown", "Industry", "Macro", "Government"})
    )
    portfolio = (
        intent in {"Portfolio", "Risk", "Watchlist"}
        or investment_recommendation
        or question_type in {"portfolio", "investment_decision", "risk"}
    ) and not education
    planner = not education
    dag = not education
    outcome = (not education) and (portfolio or has_entity) and not concept_mode
    learning = False  # never on Ask
    # Live institutional evidence packs only when bound entity + non-education
    build_ie = (not education) and has_entity and not concept_mode

    return {
        "education": education,
        "concept_mode": concept_mode,
        "as_of": as_of,
        "run_knowledge": True,
        "run_evidence": True,
        "run_planner": planner,
        "run_dag": dag,
        "run_reasoning": True,
        "run_portfolio": portfolio and not education,
        "run_decision_quality_record": True,
        "run_outcome_registration": outcome,
        "run_learning": learning,
        "run_telemetry": True,
        "build_institutional_evidence": build_ie,
        "build_portfolio_intelligence": portfolio and not education,
        "build_outcome_intelligence": outcome,
        "skips": {
            "planner": None if planner else "skipped_by_policy",
            "dag": None if dag else "skipped_by_policy",
            "portfolio": None if (portfolio and not education) else "skipped_by_policy",
            "outcome": None if outcome else "skipped_by_policy",
            "learning": "skipped_by_policy",
            "institutional_evidence": None if build_ie else "skipped_by_policy",
        },
    }
