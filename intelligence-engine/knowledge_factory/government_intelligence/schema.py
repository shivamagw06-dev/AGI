"""Institutional Government & Regulatory Intelligence (IGRI) — AGIB v2.0 Sprint 3.

Soft Knowledge Factory enrichment only.
Reasoning, Company Intelligence, Corporate Events, Decision Quality: FROZEN.
Never political opinion. Never forecast policy. Never fabricate.
"""

from __future__ import annotations

from typing import Any

IGRI_VERSION = "institutional-government-regulatory-intelligence-v2.0.1"
IGRI_SCHEMA_VERSION = "igri-schema-v2.0.1"
PROGRAMME = "AGIB v2.0 – Institutional Government & Regulatory Intelligence"
LAYER = "IGRI"
ARCHITECTURE_STATUS = "SOFT_GOVERNMENT_REGULATORY_INTELLIGENCE"
DELIVERY_PHASE = "phase_1_high_impact"

# Sprint 3 Phase 1 — highest-impact institutions only.
# These six areas drive most material policy effects on listed Indian companies.
PHASE_1_DOMAINS: tuple[str, ...] = (
    "rbi",      # monetary policy + banking regulation
    "budget",   # Union Budget / Finance Ministry
    "sebi",     # securities markets regulation
    "gst",      # GST Council
    "pli",      # Production Linked Incentive schemes
    "trade",    # import/export duties & trade policy
)

PHASE_1_BODIES: tuple[str, ...] = (
    "GOI",
    "MOF",
    "RBI",
    "SEBI",
    "GST_COUNCIL",
    "DPIIT",
    "MEITY",
    "MOC",
)

# Architecture stays open — load later without redesign.
PHASE_2_EXTENSIBLE_DOMAINS: tuple[str, ...] = (
    "mca",
    "industry",
    "state",
    "ministry",
)

COVERAGE_LEVELS: dict[int, str] = {
    0: "registry",
    1: "policy",
    2: "timeline",
    3: "relationships",
    4: "transmission",
    5: "historical_replay",
    6: "evidence",
    7: "institutional_government_intelligence",
}

INSTITUTIONAL_COMPLETE_LEVEL = 7

POLICY_TYPES: tuple[str, ...] = (
    "monetary",
    "fiscal_budget",
    "securities_regulation",
    "corporate_law",
    "tax_gst",
    "pli_industrial",
    "trade",
    "industry_regulation",
    "state_policy",
    "statutory",
)

DOMAINS: tuple[str, ...] = PHASE_1_DOMAINS + PHASE_2_EXTENSIBLE_DOMAINS

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "framework_selection": True,
    "evidence_contracts": True,
    "committee_system": True,
    "governance": True,
    "learning_engine": True,
    "decision_quality_architecture": True,
    "knowledge_factory_architecture": True,
    "universe_intelligence_architecture": True,
    "company_intelligence_architecture": True,
    "corporate_event_intelligence_architecture": True,
    "not_a_reasoning_engine": True,
    "never_political_opinion": True,
    "never_forecast_policy": True,
    "never_fabricate": True,
    "point_in_time_integrity": True,
    "immutable_policies": True,
}


def coverage_level_name(level: int) -> str:
    return COVERAGE_LEVELS.get(int(level), "unknown")


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "igri_version": IGRI_VERSION,
        "igri_schema_version": IGRI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "political_opinion": False,
        "policy_forecast": False,
        **extra,
        **payload,
    }
