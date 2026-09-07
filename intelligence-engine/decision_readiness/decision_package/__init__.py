"""Institutional Decision Package assembly."""

from __future__ import annotations

from typing import Any


def build_decision_package(
    *,
    question: str,
    thesis: dict[str, Any],
    debate: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    core = thesis.get("core_thesis") or {}
    core_statement = (
        core.get("statement") if isinstance(core, dict) else str(core)
    )
    evidence = readiness["dimensions"]["Evidence"]
    conflict = readiness["dimensions"]["Debate"]
    portfolio = readiness["dimensions"]["Portfolio"]
    monitoring = readiness["dimensions"]["Monitoring"]
    policy = readiness["dimensions"]["Policy"]
    required_follow_up = list(
        dict.fromkeys(
            evidence.get("missing_evidence", [])
            + [
                str(question)
                for question in conflict.get("outstanding_questions", [])
            ]
            + [
                str(item)
                for item in portfolio.get("constraints", [])
            ]
        )
    )
    conditions = monitoring.get("decision_conditions") or []
    no_go = [condition for condition in conditions if not condition.get("go")]
    status = readiness["decision_status"]
    executive = (
        f"{status}: the thesis scores {readiness['readiness_score_pct']}% for institutional "
        f"decision readiness. "
        + (
            "The decision may proceed subject to explicit monitoring and portfolio conditions."
            if status == "READY WITH CONDITIONS"
            else "Further research or conflict resolution is required before capital action."
            if status in ("RESEARCH REQUIRED", "NOT READY")
            else "The package satisfies the institutional decision gate."
        )
    )
    return {
        "executive_summary": executive,
        "question": question,
        "investment_thesis": core_statement,
        "decision_readiness": {
            "status": status,
            "score": readiness["readiness_score"],
            "score_pct": readiness["readiness_score_pct"],
            "confidence": readiness["confidence"],
        },
        "supporting_factors": readiness["strengths"],
        "limiting_factors": readiness["weaknesses"],
        "conditions": conditions,
        "no_go_conditions": no_go,
        "monitoring": monitoring["monitoring_plan"],
        "next_review": monitoring["monitoring_plan"]["next_review"],
        "missing_evidence": evidence.get("missing_evidence"),
        "open_questions": conflict.get("outstanding_questions"),
        "remaining_conflicts": conflict.get("remaining_conflicts"),
        "portfolio_constraints": portfolio.get("constraints"),
        "capital_allocation_readiness": portfolio.get(
            "capital_allocation_readiness"
        ),
        "capital_allocation_readiness_pct": portfolio.get(
            "capital_allocation_readiness_pct"
        ),
        "capital_state": portfolio.get("capital_state"),
        "required_follow_up": required_follow_up[:20],
        "policy_clear": policy.get("passed"),
        "committee_handoff": {
            "may_proceed": status in ("READY", "READY WITH CONDITIONS"),
            "status": status,
            "conditions_to_review": conditions,
            "minority_position": (
                (debate.get("minority_report") or [None])[0]
            ),
            "evidence_that_could_change_view": required_follow_up[:10],
        },
    }
