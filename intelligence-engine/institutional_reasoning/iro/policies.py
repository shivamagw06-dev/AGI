"""Module 8 — Planner Policies.

Different research goals produce different plans. Planner selects
the policy automatically from the objective text.
"""

from __future__ import annotations

import re
from typing import Any

from institutional_reasoning.iro.schema import ResearchTask

POLICIES_VERSION = "planner-policies-v1.0.0"

_GOAL_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("ma", re.compile(r"\b(acquire|acquisition|merger|m&a|takeover|buyout|synerg)\w*\b", re.I)),
    ("ipo", re.compile(r"\b(ipo|listing|drhp|red herring|go public)\b", re.I)),
    (
        "credit",
        re.compile(r"\b(lend|loan|credit|debt capacity|bond|solvency|covenant|repay)\w*\b", re.I),
    ),
    (
        "monitoring",
        re.compile(r"\b(monitor|track|watch|update on|any change)\w*\b", re.I),
    ),
    (
        "investment",
        re.compile(
            r"\b(invest|buy|allocate|position|add to portfolio|should i own|initiate)\w*\b",
            re.I,
        ),
    ),
)


def classify_goal(objective: str) -> dict[str, Any]:
    text = str(objective or "")
    for goal_type, pattern in _GOAL_PATTERNS:
        m = pattern.search(text)
        if m:
            return {
                "goal_type": goal_type,
                "confidence": 0.92,
                "matched": m.group(0),
                "policies_version": POLICIES_VERSION,
            }
    return {
        "goal_type": "investment",
        "confidence": 0.55,
        "matched": None,
        "reason": "default_investment_policy",
        "policies_version": POLICIES_VERSION,
    }


def _t(
    task_id: str,
    label: str,
    template: str,
    *,
    depends_on: tuple[str, ...] = (),
    committee: str = "investment",
    required: tuple[str, ...] = (),
    alternatives: tuple[str, ...] = (),
    optional: bool = False,
    deliverable: str = "",
) -> ResearchTask:
    return ResearchTask(
        task_id=task_id,
        label=label,
        question_template=template,
        depends_on=depends_on,
        committee=committee,
        required_evidence=required,
        alternatives=alternatives,
        optional=optional,
        deliverable=deliverable,
    )


def _investment_tasks() -> list[ResearchTask]:
    return [
        _t("industry", "Industry & Sector", "Is {name} sector expensive versus history?",
           committee="valuation", deliverable="sector_context"),
        _t("business_quality", "Business Quality", "Is {name} a quality business?",
           committee="business", required=("roic", "margins"), deliverable="quality_assessment"),
        _t("accounting", "Accounting Quality", "Evaluate cash flow quality for {name}.",
           committee="accounting", required=("cash_conversion", "leverage", "earnings_quality"),
           deliverable="accounting_flags"),
        _t("management", "Management & Capital Allocation", "Evaluate {name}'s capital allocation.",
           committee="business", optional=True, deliverable="capital_allocation"),
        _t("valuation", "Valuation", "Is {name} expensive versus history?",
           depends_on=("industry", "accounting"), committee="valuation",
           required=("current_pe", "historical_pe", "historical_percentile", "peer_pe"),
           alternatives=("sector_valuation", "peer_valuation"),
           deliverable="valuation_verdict"),
        _t("risk", "Risk & Downside", "What are the key risks and downside for {name}?",
           depends_on=("business_quality", "accounting"), committee="risk",
           optional=True, deliverable="risk_register"),
        _t("portfolio", "Portfolio Impact", "What is the portfolio exposure impact of {name}?",
           depends_on=("valuation", "risk"), committee="portfolio",
           optional=True, deliverable="portfolio_impact"),
    ]


def _credit_tasks() -> list[ResearchTask]:
    return [
        _t("liquidity", "Liquidity", "Evaluate working capital trends at {name}.",
           committee="accounting", deliverable="liquidity_view"),
        _t("leverage", "Leverage", "Leverage and balance sheet quality for {name}.",
           committee="accounting", required=("leverage",), deliverable="leverage_view"),
        _t("cash_flow", "Cash Flow", "Evaluate cash flow quality for {name}.",
           committee="accounting", required=("cash_conversion", "earnings_quality"),
           deliverable="cash_flow_view"),
        _t("credit_risk", "Credit Risk", "What are the key risks and downside for {name}?",
           depends_on=("liquidity", "leverage", "cash_flow"), committee="risk",
           optional=True, deliverable="credit_risk_register"),
    ]


def _ma_tasks() -> list[ResearchTask]:
    return [
        _t("target_quality", "Target Business Quality", "Is {name} a quality business?",
           committee="business", required=("roic", "margins"), deliverable="target_quality"),
        _t("competition", "Competitive Position", "Review competitive position of {name}.",
           committee="business", deliverable="competitive_map"),
        _t("synergies", "Synergies", "Evaluate {name}'s capital allocation.",
           depends_on=("target_quality",), committee="business", optional=True,
           deliverable="synergy_case"),
        _t("valuation", "Acquisition Valuation", "Is {name} expensive versus history?",
           depends_on=("target_quality", "competition"), committee="valuation",
           required=("current_pe", "historical_pe", "historical_percentile", "peer_pe"),
           alternatives=("sector_valuation", "peer_valuation"), deliverable="deal_valuation"),
        _t("integration_risk", "Integration Risk", "What are the key risks and downside for {name}?",
           depends_on=("synergies", "valuation"), committee="risk", optional=True,
           deliverable="integration_risk"),
    ]


def _ipo_tasks() -> list[ResearchTask]:
    return [
        _t("growth", "Growth Profile", "Is {name} a quality business?",
           committee="business", required=("roic", "margins"), deliverable="growth_profile"),
        _t("governance", "Governance", "Evaluate {name}'s capital allocation.",
           committee="business", optional=True, deliverable="governance_view"),
        _t("market", "Market & Sector", "Is {name} sector expensive versus history?",
           committee="valuation", deliverable="market_context"),
        _t("valuation", "IPO Valuation", "Is {name} expensive versus history?",
           depends_on=("growth", "market"), committee="valuation",
           required=("current_pe", "historical_pe", "historical_percentile", "peer_pe"),
           alternatives=("sector_valuation", "peer_valuation"), deliverable="ipo_valuation"),
    ]


def _monitoring_tasks() -> list[ResearchTask]:
    return [
        _t("valuation", "Valuation Check", "Is {name} expensive versus history?",
           committee="valuation",
           required=("current_pe", "historical_pe", "historical_percentile", "peer_pe"),
           alternatives=("sector_valuation", "peer_valuation"), deliverable="valuation_delta"),
        _t("accounting", "Accounting Check", "Evaluate cash flow quality for {name}.",
           committee="accounting", required=("cash_conversion", "leverage", "earnings_quality"),
           deliverable="accounting_delta"),
    ]


_POLICY_TASKS = {
    "investment": _investment_tasks,
    "credit": _credit_tasks,
    "ma": _ma_tasks,
    "ipo": _ipo_tasks,
    "monitoring": _monitoring_tasks,
}


def tasks_for(goal_type: str) -> list[ResearchTask]:
    fn = _POLICY_TASKS.get(str(goal_type or "").lower()) or _investment_tasks
    return fn()


def policy_snapshot() -> dict[str, Any]:
    return {
        "policies_version": POLICIES_VERSION,
        "goal_types": sorted(_POLICY_TASKS),
        "task_counts": {k: len(v()) for k, v in _POLICY_TASKS.items()},
    }
