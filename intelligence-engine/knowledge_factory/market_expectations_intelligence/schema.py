"""Institutional Market Expectations Intelligence (IMEI) — AGIB v2.0 Sprint 7.

Soft Knowledge Factory enrichment only.
Teaches: markets price expectations, not reality.
NOT broker report ingestion. NOT recommendation aggregation. NOT sentiment.
NOT a prediction engine. Soft-wire only.

Phase 1: company guidance, reported results, AGIB timestamped forecasts.
Phase 2 (optional): licensed external consensus — modular collector; UNKNOWN if unavailable.
"""

from __future__ import annotations

from typing import Any

IMEI_VERSION = "institutional-market-expectations-intelligence-v2.0.0"
IMEI_SCHEMA_VERSION = "imei-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Market Expectations Intelligence"
LAYER = "IMEI"
ARCHITECTURE_STATUS = "SOFT_MARKET_EXPECTATIONS_INTELLIGENCE"
DELIVERY_PHASE = "phase_1_public_auditable"
UNKNOWN = "UNKNOWN"

# Phase 1 — public, auditable expectation sources (no proprietary broker consensus).
PHASE_1_SOURCES: tuple[str, ...] = (
    "company_guidance",
    "company_earnings_release",
    "exchange_disclosure",
    "investor_presentation",
    "agib_internal_forecast",
)

# Phase 2 — modular; never assumed present.
PHASE_2_SOURCES: tuple[str, ...] = (
    "licensed_consensus_feed",
)

METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "ebit",
    "eps",
    "margin",
    "capex",
    "dividend",
    "roe",
    "roic",
    "cash_flow",
    "growth",
    "target_valuation",
)

EXPECTATION_KINDS: tuple[str, ...] = (
    "guidance",
    "internal_forecast",
    "consensus_proxy",  # Phase-1 proxy from guidance/internal only
    "licensed_consensus",  # Phase-2 only
    "actual",
)

QUALITY_GATES: tuple[str, ...] = (
    "source",
    "provenance",
    "available_from",
    "revision_consistency",
    "future_leakage",
    "duplicate",
    "validation",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "governance": True,
    "committee_system": True,
    "evidence_contracts": True,
    "decision_quality_architecture": True,
    "universe_intelligence_architecture": True,
    "company_intelligence_architecture": True,
    "corporate_event_intelligence_architecture": True,
    "government_intelligence_architecture": True,
    "industry_value_chain_intelligence_architecture": True,
    "economic_relationship_intelligence_architecture": True,
    "alternative_data_intelligence_architecture": True,
    "historical_intelligence": True,
    "sector_intelligence_architecture": True,
    "macro_intelligence_architecture": True,
    "knowledge_factory_architecture": True,
    "planner": True,
    "framework_selection": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "not_a_prediction_engine": True,
    "not_broker_report_ingestion": True,
    "not_recommendation_aggregation": True,
    "not_sentiment_analysis": True,
    "never_fabricate": True,
    "never_scrape_broker_reports": True,
    "point_in_time_integrity": True,
    "soft_wire_only": True,
    "phase_2_consensus_optional": True,
}


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "imei_version": IMEI_VERSION,
        "imei_schema_version": IMEI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "delivery_phase": DELIVERY_PHASE,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "reasoning_changed": False,
        **extra,
        **payload,
    }
