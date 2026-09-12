"""IAP — Institutional Analytical Playbooks schemas."""

from __future__ import annotations

from typing import Any

IAP_VERSION = "institutional-playbooks-v1.0.0"
PROGRAMME = "AGIB v3.5 – Institutional Analytical Playbooks · Sprint 1 Playbook Engine"
MODULE_CODE = "IAP"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_playbook_selection": True,
    "guides_reasoning_does_not_replace": True,
}

CATEGORIES: tuple[str, ...] = (
    "company",
    "valuation",
    "industry",
    "macro",
    "government",
    "documents",
    "accounting",
    "investment_committee",
    "replay",
    "quality",
)

# Target V1 allocation (≈50)
TARGET_COUNTS: dict[str, int] = {
    "company": 12,
    "industry": 8,
    "valuation": 8,
    "macro": 8,
    "government": 5,
    "documents": 5,
    "investment_committee": 4,
}
