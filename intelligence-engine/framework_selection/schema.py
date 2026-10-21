"""IFSE — Institutional Framework Selection Engine schemas."""

from __future__ import annotations

from typing import Any

IFSE_VERSION = "framework-selection-v1.1.0"  # Sprint 3.3 cue overlays + sector enrichment
PROGRAMME = "AGIB v3.4 – Institutional Answer Excellence · Track C Framework Selection"
MODULE_CODE = "IFSE"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_framework_selection": True,
}

# Role labels for multi-framework composition
ROLES: tuple[str, ...] = ("primary", "secondary", "supporting")

SECTORS: tuple[str, ...] = (
    "banks",
    "insurance",
    "nbfc",
    "it_services",
    "consumer_staples",
    "hospitals",
    "airlines",
    "cement",
    "steel",
    "conglomerates",
    "real_estate",
    "utilities",
    "telecom",
    "industrials",
    "pharma",
    "auto",
    "generic",
)
