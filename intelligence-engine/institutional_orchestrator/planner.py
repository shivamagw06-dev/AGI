"""UAG-01 query planning — builds deterministic execution plans over registered objects."""

from __future__ import annotations

from typing import Sequence

from institutional_orchestrator.models import ExecutionStep, InstitutionalQuery
from institutional_orchestrator.object_registry import get, match_routes
from institutional_orchestrator.schema import ORCHESTRATOR_VERSION

# Intent → ordered object types (lineage-aware defaults)
_INTENT_PLANS: dict[str, tuple[str, ...]] = {
    "Committee": (
        "CommitteeResolution",
        "PortfolioDecision",
        "PolicyAssessment",
        "PortfolioRisk",
        "CompanyDecision",
    ),
    "Policy": (
        "PolicyAssessment",
        "PortfolioRisk",
        "PortfolioDecision",
        "CommitteeResolution",
        "Observation",
    ),
    "Risk": (
        "PortfolioRisk",
        "PortfolioGraph",
        "PolicyAssessment",
        "PortfolioDecision",
    ),
    "Portfolio Analysis": (
        "PortfolioDecision",
        "PortfolioRisk",
        "PolicyAssessment",
        "PortfolioGraph",
        "CommitteeResolution",
    ),
    "Company Analysis": (
        "CompanyDecision",
        "Forecast",
        "Observation",
        "Research",
        "PortfolioDecision",
    ),
    "Observation": (
        "Observation",
        "Forecast",
        "PortfolioRisk",
        "PolicyAssessment",
        "CommitteeResolution",
    ),
    "Forecast": ("Forecast", "Observation", "CompanyDecision", "Research"),
    "Comparison": ("ComparisonEvidence",),
    "Macro": ("Forecast", "Observation", "Research", "PortfolioRisk"),
    "Market": ("Observation", "Forecast", "Research", "PortfolioRisk"),
    "History": ("CommitteeResolution", "PortfolioDecision", "CompanyDecision", "Observation"),
    "Timeline": ("Observation", "CommitteeResolution", "CompanyDecision"),
    "Research": ("Research", "CompanyDecision", "Forecast", "Observation"),
    "Search": ("PortfolioGraph", "CompanyDecision", "Research"),
}

_PLANNER_FOR_OBJECT = {
    "CompanyDecision": "company",
    "Forecast": "company",
    "Research": "company",
    "ComparisonEvidence": "company",
    "PortfolioGraph": "portfolio",
    "PortfolioRisk": "portfolio",
    "PortfolioDecision": "portfolio",
    "PolicyAssessment": "governance",
    "CommitteeResolution": "governance",
    "Observation": "market",
}


def plan_query(
    *,
    query_id: str,
    question: str,
    intent: str,
    entities: Sequence[str] = (),
    generated_at: str = "",
) -> InstitutionalQuery:
    route_hits = match_routes(question)
    # A comparison is a factual multi-company retrieval.  Do not pull a
    # single-company decision object merely because the question mentions
    # valuation; it can be unavailable and is not evidence for a comparison.
    if intent == "Comparison":
        route_hits = [r for r in route_hits if r.object_type == "ComparisonEvidence"]
    planned_types: list[str] = []

    # Route hits first (capability discovery)
    for reg in route_hits:
        if reg.object_type not in planned_types:
            planned_types.append(reg.object_type)

    # Intent defaults fill gaps / enforce lineage order
    for ot in _INTENT_PLANS.get(intent, _INTENT_PLANS["Search"]):
        if ot not in planned_types:
            planned_types.append(ot)

    # Cross-object special case: observations → policy
    q = (question or "").lower()
    if "observation" in q and "policy" in q:
        for ot in ("Observation", "PortfolioGraph", "PolicyAssessment", "CommitteeResolution"):
            if ot not in planned_types:
                planned_types.append(ot)

    # Committee "why reduce X" needs company + full stack
    if intent == "Committee" or ("why" in q and ("reduce" in q or "defer" in q or "committee" in q)):
        for ot in (
            "CommitteeResolution",
            "PortfolioDecision",
            "PolicyAssessment",
            "PortfolioRisk",
            "CompanyDecision",
        ):
            if ot not in planned_types:
                planned_types.insert(0 if ot == "CommitteeResolution" else len(planned_types), ot)
        # Stable unique order for committee why
        ordered = []
        for ot in (
            "CommitteeResolution",
            "PortfolioDecision",
            "PolicyAssessment",
            "PortfolioRisk",
            "CompanyDecision",
        ):
            if ot in planned_types and ot not in ordered:
                ordered.append(ot)
        for ot in planned_types:
            if ot not in ordered:
                ordered.append(ot)
        planned_types = ordered

    steps: list[ExecutionStep] = []
    planners: list[str] = []
    for i, ot in enumerate(planned_types):
        reg = get(ot)
        provider = reg.provider if reg else "unknown"
        planner = (reg.planner if reg else _PLANNER_FOR_OBJECT.get(ot, "company"))
        if planner not in planners:
            planners.append(planner)
        steps.append(
            ExecutionStep(
                step_id=f"step-{i+1}",
                object_type=ot,
                provider=provider,
                purpose=f"Retrieve {ot} for intent {intent}",
                status="planned",
            )
        )

    return InstitutionalQuery(
        query_id=query_id,
        question=question,
        intent=intent,
        entities=tuple(entities),
        planners=tuple(planners),
        required_objects=tuple(planned_types),
        execution_plan=tuple(steps),
        diagnostics={
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "route_hits": [r.object_type for r in route_hits],
        },
        generated_at=generated_at,
    )
