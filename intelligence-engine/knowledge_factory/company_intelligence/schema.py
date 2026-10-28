"""Institutional Company Intelligence (ICI) — AGIB v2.0 Sprint 1.

Soft Knowledge Factory enrichment only.
Phases 1–7, KF architecture, Universe Intelligence, Decision Quality: FROZEN.
Never fabricate qualitative fields — use UNKNOWN when unavailable.
"""

from __future__ import annotations

from typing import Any

ICI_VERSION = "institutional-company-intelligence-v2.0.0"
ICI_SCHEMA_VERSION = "ici-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Company Intelligence"
LAYER = "ICI"
ARCHITECTURE_STATUS = "SOFT_COMPANY_INTELLIGENCE"

COVERAGE_LEVELS: dict[int, str] = {
    0: "discovered",
    1: "identity",
    2: "business_model",
    3: "products_segments",
    4: "management_ownership",
    5: "competition_risks",
    6: "timeline",
    7: "institutional_company_intelligence",
}

INSTITUTIONAL_COMPLETE_LEVEL = 7

MODULES: tuple[str, ...] = (
    "identity",
    "business_model",
    "products",
    "segments",
    "customers",
    "management",
    "ownership",
    "capital_allocation",
    "competition",
    "business_quality",
    "business_risk",
    "timeline",
    "knowledge_links",
)

# Sprint 1A core / Sprint 1B extension
SPRINT_1A_MODULES: tuple[str, ...] = (
    "identity",
    "business_model",
    "products",
    "segments",
    "customers",
    "management",
    "ownership",
)

SPRINT_1B_MODULES: tuple[str, ...] = (
    "capital_allocation",
    "competition",
    "business_quality",
    "business_risk",
    "timeline",
    "knowledge_links",
)

QUALITY_GATES: tuple[str, ...] = (
    "identity",
    "business_model",
    "products",
    "segments",
    "management",
    "ownership",
    "timeline",
    "provenance",
    "validation",
)

PROVENANCE_FIELDS: tuple[str, ...] = (
    "source",
    "retrieved_at",
    "validated_at",
    "collector",
    "confidence",
    "derived_from",
    "version",
)

UNKNOWN = "UNKNOWN"

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory_architecture": True,
    "universe_intelligence_architecture": True,
    "decision_quality_architecture": True,
    "governance": True,
    "committees": True,
    "planner": True,
    "evidence_contracts": True,
    "framework_execution": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "never_fabricate": True,
}


def coverage_level_name(level: int) -> str:
    return COVERAGE_LEVELS.get(int(level), "unknown")


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "ici_version": ICI_VERSION,
        "ici_schema_version": ICI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        **extra,
        **payload,
    }
