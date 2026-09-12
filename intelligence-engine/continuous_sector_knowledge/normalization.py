"""Normalize validated drafts into versioned Sector Knowledge Objects."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import (
    Outlook,
    RawSectorDraft,
    SectorKnowledgeObject,
    Trend,
    canonicalize,
)
from continuous_sector_knowledge.store import STORE


def _outlook_from(cat: dict[str, Any], macro: dict[str, Any], sector_key: str) -> Outlook:
    base = str(cat.get("default_outlook") or "Neutral")
    # Soft macro overlays for rate-sensitive sectors
    repo = macro.get("Repo Rate")
    cpi = macro.get("CPI")
    if sector_key in {"banking", "nbfc", "auto", "real_estate"} and repo is not None:
        try:
            if float(repo) <= 6.0:
                return "Positive"
        except (TypeError, ValueError):
            pass
    if sector_key == "fmcg" and cpi is not None:
        try:
            if float(cpi) >= 6.0:
                return "Negative"
            if float(cpi) <= 4.0:
                return "Positive"
        except (TypeError, ValueError):
            pass
    if base in {"Positive", "Neutral", "Negative", "Mixed"}:
        return base  # type: ignore[return-value]
    return "Neutral"


def _trend(value: Any) -> Trend:
    if value in {"Improving", "Stable", "Deteriorating", "Mixed", "Unknown"}:
        return value  # type: ignore[return-value]
    return "Unknown"


def normalize_draft(draft: RawSectorDraft) -> SectorKnowledgeObject:
    key = canonicalize(draft.sector_key) or draft.sector_key
    prior = STORE.latest(key)
    version = (prior.version + 1) if prior else 1
    parent = prior.sko_id if prior else None
    cat = draft.catalog or {}
    macro = draft.macro_tips or {}

    outlook = _outlook_from(cat, macro, key)
    leaders = list(cat.get("leaders") or [])
    company_cov = sum(1 for c in draft.company_tips if c.get("has_catalog") or c.get("ticker"))

    # Confidence rises with layered sources + company coverage
    confidence = 0.55 + 0.05 * min(5, len(draft.source_layers)) + 0.02 * min(10, company_cov)
    if "MRI" in draft.source_layers:
        confidence += 0.05
    if macro.get("Repo Rate") is not None:
        confidence += 0.03
    confidence = round(min(0.95, confidence), 3)

    normalized = {
        "sector_key": key,
        "group": cat.get("group"),
        "macro_tips": {k: v for k, v in macro.items() if k not in {"providers_queried", "gateway"}},
        "market_tips": draft.market_tips,
        "event_n": len(draft.event_tips),
        "company_tickers": [c.get("ticker") for c in draft.company_tips],
        "research": draft.research_tips,
        "trigger": draft.trigger,
        "prior_outlook": prior.current_outlook if prior else None,
    }

    return SectorKnowledgeObject(
        sector_key=key,
        label=str(cat.get("label") or draft.label),
        current_outlook=outlook,
        revenue_trend=_trend(cat.get("revenue_trend")),
        margin_trend=_trend(cat.get("margin_trend")),
        valuation=cat.get("valuation_note"),
        growth_drivers=list(cat.get("growth_drivers") or []),
        key_risks=list(cat.get("key_risks") or []),
        government_policy=list(cat.get("government_policy") or []),
        macro_sensitivity=dict(cat.get("macro_sensitivity") or {}),
        leading_companies=leaders,
        market_share_notes=list(cat.get("market_share_notes") or []),
        sector_confidence=confidence,
        knowledge_freshness_sec=0,
        version=version,
        parent_sko_id=parent,
        source_layers=list(draft.source_layers),
        company_coverage=company_cov,
        normalized=normalized,
        provenance={
            "draft_id": draft.draft_id,
            "mode": "derived_continuous",
            "ask_triggered": False,
            "providers_queried": [],
        },
        trigger=draft.trigger,
    )
