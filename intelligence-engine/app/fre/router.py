"""Step 3 — Source router — map retrieval tasks to authority tiers."""

from __future__ import annotations

from typing import Any

from app.fre.authority import source_tier
from app.fre.models import QueryPlan, RetrievalTask


TIER_SOURCES: dict[int, list[str]] = {
    1: ["company_ir", "annual_report", "quarterly_report", "investor_presentation", "exchange_filing"],
    2: ["nse", "bse", "sebi", "rbi", "government", "pib", "mca"],
    3: ["world_bank", "imf", "oecd", "fred"],
    4: ["reuters", "bloomberg", "cnbc", "moneycontrol", "economic_times", "business_standard", "mint"],
    5: ["industry_report", "trade_association", "research_publication"],
    6: ["general_web"],
}


def route_task(task: RetrievalTask) -> dict[str, Any]:
    sources: list[str] = []
    for tier in task.preferred_tiers or [1, 2, 3, 4]:
        for src in TIER_SOURCES.get(tier, []):
            if src not in sources:
                sources.append(src)
    # Prefer document_type-aligned sources first
    ordered = []
    for dt in task.document_types:
        if dt in sources and dt not in ordered:
            ordered.append(dt)
    for src in sources:
        if src not in ordered:
            ordered.append(src)
    return {
        "task_id": task.task_id,
        "description": task.description,
        "document_types": task.document_types,
        "sources": ordered,
        "min_tier": min(task.preferred_tiers) if task.preferred_tiers else 6,
        "allow_general_web": 6 in (task.preferred_tiers or []),
        "company": task.company,
        "symbol": task.symbol,
    }


def route_plan(plan: QueryPlan) -> list[dict[str, Any]]:
    return [route_task(t) for t in plan.tasks]


def filter_by_authority(items: list[dict[str, Any]], *, min_authority: int = 4) -> list[dict[str, Any]]:
    out = []
    for item in items:
        tier = source_tier(item.get("document_type"), item.get("source"))
        auth = int(item.get("authority") or (11 - tier))
        if auth >= min_authority or tier <= 4:
            out.append(item)
    return out
