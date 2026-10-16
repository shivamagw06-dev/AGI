"""Institutional Alternative Data Intelligence (IADI) — AGIB v2.0 Sprint 6.

Soft Knowledge Factory enrichment only.
High-signal real-economy observations that often precede earnings.
NOT a prediction engine. NOT a reasoning change. Soft-wire only.
Never fabricate. Never interpolate unsupported values. UNKNOWN when unavailable.
"""

from __future__ import annotations

from typing import Any

IADI_VERSION = "institutional-alternative-data-intelligence-v2.0.0"
IADI_SCHEMA_VERSION = "iadi-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Alternative Data Intelligence"
LAYER = "IADI"
ARCHITECTURE_STATUS = "SOFT_ALTERNATIVE_DATA_INTELLIGENCE"
DELIVERY_PHASE = "phase_1_high_signal"
UNKNOWN = "UNKNOWN"

# Phase 1 — 10 high-signal, consistently published datasets with listed-company links.
# Broader domains (property, telecom, full payments stack, etc.) remain extensible shells.
PHASE_1_DATASETS: tuple[str, ...] = (
    "upi_transactions",       # NPCI — consumer / digital payments
    "electricity_demand",     # Grid India / POSOCO — industrial activity
    "iip_manufacturing",      # MOSPI — manufacturing (public; PMI = licensed later)
    "railway_freight",        # Indian Railways — logistics / bulk
    "port_cargo",             # Ministry / ports — trade logistics
    "vehicle_registrations",  # VAHAN aggregates — auto demand
    "air_passengers_domestic",# DGCA — travel / consumer mobility
    "bank_credit_growth",     # RBI — credit cycle
    "rainfall_monsoon",       # IMD — agriculture / rural
    "gst_collections",        # GSTN published aggregates — formal economy
)

PHASE_1_DOMAINS: tuple[str, ...] = (
    "payments",
    "energy",
    "manufacturing",
    "transport",
    "consumer",
    "banking",
    "agriculture",
    "trade",
)

# Architecture stays open — load later without redesign.
PHASE_2_EXTENSIBLE_DATASETS: tuple[str, ...] = (
    "neft_rtgs_imps",
    "fastag_toll",
    "cement_dispatch",
    "steel_production",
    "pmi_manufacturing",  # S&P Global — subject to licensing
    "housing_sales",
    "wireless_subscribers",
    "trade_balance",
    "coal_stocks",
    "metro_ridership",
)

FREQUENCIES: tuple[str, ...] = ("daily", "weekly", "monthly", "quarterly", "seasonal", "annual")

QUALITY_GATES: tuple[str, ...] = (
    "source",
    "provenance",
    "available_from",
    "validation",
    "duplicate",
    "replay",
    "future_leakage",
    "derived_metrics",
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
    "historical_intelligence": True,
    "sector_intelligence_architecture": True,
    "macro_intelligence_architecture": True,
    "knowledge_factory_architecture": True,
    "planner": True,
    "framework_selection": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "not_a_prediction_engine": True,
    "never_fabricate": True,
    "never_interpolate_unsupported": True,
    "point_in_time_integrity": True,
    "soft_wire_only": True,
}


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "iadi_version": IADI_VERSION,
        "iadi_schema_version": IADI_SCHEMA_VERSION,
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
