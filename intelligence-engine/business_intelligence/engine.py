"""FIRE-03 orchestration — build packs from extracted BusinessFacts."""

from __future__ import annotations

from typing import Any

from business_intelligence.evidence import confidence_distribution
from business_intelligence.extractors import extract_all_facts
from business_intelligence.inventory import load_document_bundles
from business_intelligence.schema import (
    CAPITAL_CATEGORIES,
    CAT_GEOGRAPHY,
    CAT_GOVERNANCE,
    CAT_OPPORTUNITY,
    CAT_PRODUCTS,
    CAT_REVENUE_MODEL,
    CAT_RISK,
    CAT_SEGMENT_ANALYSIS,
    CAT_SEGMENTS,
    CAT_SERVICES,
    GUIDANCE_CATEGORIES,
    OUTPUT_PACKS,
    PACK_BUSINESS_PROFILE,
    PACK_CAPITAL_ALLOCATION,
    PACK_GUIDANCE_SUMMARY,
    PACK_MANAGEMENT_STRATEGY,
    PACK_OPPORTUNITY_REGISTER,
    PACK_RISK_REGISTER,
    PACK_SEGMENT_ANALYSIS,
    PROFILE_CATEGORIES,
    STRATEGY_CATEGORIES,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _filter(facts: list[dict[str, Any]], categories: frozenset[str] | set[str]) -> list[dict[str, Any]]:
    return [f for f in facts if f.get("category") in categories]


def build_packs(facts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        PACK_BUSINESS_PROFILE: _filter(facts, PROFILE_CATEGORIES),
        PACK_MANAGEMENT_STRATEGY: _filter(facts, STRATEGY_CATEGORIES),
        PACK_SEGMENT_ANALYSIS: [
            f for f in facts if f.get("category") in {CAT_SEGMENTS, CAT_SEGMENT_ANALYSIS}
        ],
        PACK_RISK_REGISTER: [f for f in facts if f.get("category") == CAT_RISK],
        PACK_OPPORTUNITY_REGISTER: [f for f in facts if f.get("category") == CAT_OPPORTUNITY],
        PACK_GUIDANCE_SUMMARY: _filter(facts, GUIDANCE_CATEGORIES),
        PACK_CAPITAL_ALLOCATION: _filter(facts, CAPITAL_CATEGORIES),
    }


def mission_control_board(
    *,
    n_documents: int,
    pages_indexed: int,
    facts: list[dict[str, Any]],
    packs: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    dist = confidence_distribution(facts)
    return {
        "business_documents_processed": n_documents,
        "pages_indexed": pages_indexed,
        "facts_extracted": len(facts),
        "segment_coverage": len(packs.get(PACK_SEGMENT_ANALYSIS) or []),
        "risk_coverage": len(packs.get(PACK_RISK_REGISTER) or []),
        "guidance_extracted": len(packs.get(PACK_GUIDANCE_SUMMARY) or []),
        "strategy_facts": len(packs.get(PACK_MANAGEMENT_STRATEGY) or []),
        "governance_facts": len([f for f in facts if f.get("category") == CAT_GOVERNANCE]),
        "confidence_distribution": dist,
        "products_services_facts": len(
            [f for f in facts if f.get("category") in {CAT_PRODUCTS, CAT_SERVICES, CAT_REVENUE_MODEL}]
        ),
        "geographic_facts": len([f for f in facts if f.get("category") == CAT_GEOGRAPHY]),
    }


def build_intelligence(
    ticker: str,
    *,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    inv = load_document_bundles(ticker, documents=documents)
    bundles = inv.get("bundles") or []
    facts = extract_all_facts(bundles)
    packs = build_packs(facts)
    mc = mission_control_board(
        n_documents=int(inv.get("n_documents") or 0),
        pages_indexed=int(inv.get("pages_indexed") or 0),
        facts=facts,
        packs=packs,
    )
    sources = []
    for b in bundles:
        doc = b.get("document") or {}
        sources.append(
            {
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "type": doc.get("type"),
                "published_date": doc.get("published_date"),
                "reporting_period": b.get("reporting_period") or doc.get("reporting_period"),
                "pages": b.get("pages"),
                "source": doc.get("source"),
            }
        )
    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": inv.get("ticker"),
        "facts": facts,
        "n_facts": len(facts),
        "packs": packs,
        "output_packs": list(OUTPUT_PACKS),
        "sources": sources,
        "mission_control": mc,
        "inventory_notes": inv.get("notes") or [],
        "read_only": True,
        "uses_llm": False,
        "buy_sell": False,
        "forecast": False,
        "issues_recommendations": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "as_of": now_iso(),
    }
