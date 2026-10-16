"""PUB-01 Publication Planner — plan composition steps; never analyzes."""

from __future__ import annotations

from typing import Any, Optional

from institutional_publishing.models import PublicationPlan
from institutional_publishing.publication_registry import get
from institutional_publishing.schema import REQUIRED_SOURCES, TYPE_TO_CATEGORY


def plan_publication(
    publication_type: str,
    *,
    ticker: str = "",
    portfolio_id: str = "agi-core-equity",
    query: str = "",
) -> PublicationPlan:
    reg = get(publication_type)
    required = tuple(reg.required_sources) if reg else REQUIRED_SOURCES.get(publication_type, ())
    template = reg.template if reg else publication_type

    # Composition order mirrors institutional lineage — retrieval plan only
    steps = (
        "Resolve publication type",
        "Load template (presentation only)",
        "Retrieve immutable source objects",
        "Assemble sections from sources",
        "Attach evidence lineage",
        "Build publication manifest",
        "Render artifacts",
    )

    # Intent hints from free-text (routing only — no analysis)
    q = (query or "").lower()
    inferred_type = publication_type
    if not publication_type and q:
        if "committee" in q:
            inferred_type = "InvestmentCommitteePack"
        elif "morning" in q:
            inferred_type = "MorningBrief"
        elif "portfolio" in q and "review" in q:
            inferred_type = "PortfolioReview"
        elif "risk" in q:
            inferred_type = "RiskSummary"
        elif "banking" in q or "weekly" in q:
            inferred_type = "WeeklyClientReport"
        elif ticker or "company" in q:
            inferred_type = "CompanyResearchNote"
        else:
            inferred_type = "MorningBrief"
        reg = get(inferred_type)
        required = tuple(reg.required_sources) if reg else REQUIRED_SOURCES.get(inferred_type, ())
        template = reg.template if reg else inferred_type

    # Weekly banking report style path
    if "banking" in q or "sector" in q:
        steps = (
            "Sector context",
            "Companies",
            "Observations",
            "Decisions",
            "Relationships",
            "Research",
            "Publication",
        )

    return PublicationPlan(
        publication_type=inferred_type or publication_type,
        template=template,
        required_sources=required,
        context={
            "ticker": str(ticker or "").upper(),
            "portfolio_id": portfolio_id,
            "category": TYPE_TO_CATEGORY.get(inferred_type or publication_type, ""),
            "query": query,
            "analyzes": False,
        },
        steps=steps,
    )


def resolve_type_from_request(payload: Optional[dict[str, Any]] = None) -> str:
    body = dict(payload or {})
    explicit = str(body.get("publication_type") or body.get("type") or "").strip()
    if explicit:
        return explicit
    q = str(body.get("query") or body.get("question") or body.get("q") or "").lower()
    if "committee" in q:
        return "InvestmentCommitteePack"
    if "morning" in q:
        return "MorningBrief"
    if "evening" in q:
        return "EveningBrief"
    if "macro" in q:
        return "MacroUpdate"
    if "portfolio review" in q or ("portfolio" in q and "review" in q):
        return "PortfolioReview"
    if "risk" in q and "summary" in q:
        return "RiskSummary"
    if "policy" in q:
        return "PolicyReview"
    if "client" in q or "weekly" in q:
        return "WeeklyClientReport"
    if "company" in q or body.get("ticker"):
        return "CompanyResearchNote"
    return "MorningBrief"
