"""Workflow registry — ordered playbook composition per research workflow."""

from __future__ import annotations

from typing import Any


def _wf(
    key: str,
    *,
    objective: str,
    playbooks: tuple[tuple[str, str], ...],
    acceptance_tests: tuple[str, ...],
) -> dict[str, Any]:
    """Build workflow: (playbook_key, status_label)."""
    return {
        "workflow_key": key,
        "name": key.replace("_", " ").title(),
        "decision_objective": objective,
        "playbooks": [{"playbook_key": pk, "status_label": label} for pk, label in playbooks],
        "playbook_keys": [pk for pk, _ in playbooks],
        "status_labels": [label for _, label in playbooks],
        "acceptance_tests": acceptance_tests,
    }


WORKFLOW_REGISTRY: dict[str, dict[str, Any]] = {
    "investment_opportunity_evaluation": _wf(
        "investment_opportunity_evaluation",
        objective="Evaluate Investment Opportunity",
        playbooks=(
            ("business_quality_assessment", "Business Quality"),
            ("financial_analysis", "Financial Quality"),
            ("management_assessment", "Management"),
            ("valuation_assessment", "Valuation"),
            ("risk_assessment", "Risks"),
            ("peer_comparison", "Peer Comparison"),
            ("portfolio_assessment", "Portfolio Fit"),
            ("investment_thesis", "Thesis Stress Test"),
        ),
        acceptance_tests=(
            "Correct workflow selected",
            "Required intelligence collected",
            "Research conclusion generated",
            "Next Best Research Question generated",
            "Research status updated",
            "No prohibited language",
        ),
    ),
    "valuation_review": _wf(
        "valuation_review",
        objective="Understand Valuation",
        playbooks=(
            ("valuation_assessment", "Valuation"),
            ("peer_comparison", "Peer Comparison"),
            ("forecast_analysis", "Growth Assumptions"),
            ("investment_thesis", "Thesis Review"),
        ),
        acceptance_tests=("Correct workflow selected", "Research conclusion generated", "No prohibited language"),
    ),
    "company_deep_dive": _wf(
        "company_deep_dive",
        objective="Understand Company",
        playbooks=(
            ("business_quality_assessment", "Business Quality"),
            ("financial_analysis", "Financial Quality"),
            ("management_assessment", "Management"),
            ("competitive_position", "Competitive Position"),
            ("valuation_assessment", "Valuation"),
            ("risk_assessment", "Risks"),
        ),
        acceptance_tests=("Correct workflow selected", "Evidence available", "No prohibited language"),
    ),
    "earnings_review": _wf(
        "earnings_review",
        objective="Understand Earnings",
        playbooks=(
            ("earnings_review", "Earnings Review"),
            ("financial_analysis", "Financial Quality"),
            ("forecast_analysis", "Forecast Analysis"),
            ("investment_thesis", "Thesis Impact"),
        ),
        acceptance_tests=("Correct workflow selected", "Research conclusion generated", "No prohibited language"),
    ),
    "peer_comparison": _wf(
        "peer_comparison",
        objective="Compare Companies",
        playbooks=(
            ("peer_comparison", "Peer Comparison"),
            ("business_quality_assessment", "Business Quality"),
            ("valuation_assessment", "Valuation"),
        ),
        acceptance_tests=("Correct workflow selected", "No prohibited language"),
    ),
    "portfolio_review": _wf(
        "portfolio_review",
        objective="Review Portfolio",
        playbooks=(
            ("portfolio_assessment", "Portfolio Review"),
            ("risk_assessment", "Concentration Risk"),
            ("portfolio_assessment", "Opportunity Cost"),
        ),
        acceptance_tests=("Correct workflow selected", "No prohibited language"),
    ),
    "market_overview": _wf(
        "market_overview",
        objective="Understand Market",
        playbooks=(
            ("market_overview", "Market Overview"),
            ("macro_analysis", "Macro Assessment"),
            ("sector_analysis", "Sector Rotation"),
        ),
        acceptance_tests=("Correct workflow selected", "No prohibited language"),
    ),
    "educational_workflow": _wf(
        "educational_workflow",
        objective="Learn Investment Concepts",
        playbooks=(("education", "Concept"), ("education", "Application")),
        acceptance_tests=("Correct workflow selected", "No prohibited language"),
    ),
}

_OBJECTIVE_TO_WORKFLOW: dict[str, str] = {
    "Evaluate Investment Opportunity": "investment_opportunity_evaluation",
    "Understand Company": "company_deep_dive",
    "Understand Valuation": "valuation_review",
    "Understand Business Quality": "company_deep_dive",
    "Understand Financial Strength": "company_deep_dive",
    "Understand Management": "company_deep_dive",
    "Understand Risk": "company_deep_dive",
    "Understand Earnings": "earnings_review",
    "Understand Competitive Position": "peer_comparison",
    "Compare Companies": "peer_comparison",
    "Compare Sectors": "market_overview",
    "Understand Macro Impact": "market_overview",
    "Review Portfolio": "portfolio_review",
    "Review Watchlist": "portfolio_review",
    "Review Thesis": "earnings_review",
    "Monitor Existing Investment": "portfolio_review",
    "Understand Market": "market_overview",
    "Learn Investment Concepts": "educational_workflow",
}


def get_workflow(key: str) -> dict[str, Any] | None:
    return WORKFLOW_REGISTRY.get(key)


def resolve_workflow_for_objective(objective: str) -> dict[str, Any]:
    key = _OBJECTIVE_TO_WORKFLOW.get(objective, "company_deep_dive")
    return get_workflow(key) or get_workflow("company_deep_dive") or {}
