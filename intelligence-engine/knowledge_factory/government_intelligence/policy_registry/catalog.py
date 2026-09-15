"""Policy domain index — Phase 1 active vs Phase 2 extensible."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.schema import PHASE_1_DOMAINS, PHASE_2_EXTENSIBLE_DOMAINS

DOMAIN_INDEX: dict[str, dict[str, Any]] = {
    "rbi": {"label": "RBI Intelligence", "body": "RBI", "policy_type": "monetary", "phase": "phase_1"},
    "budget": {"label": "Union Budget / Finance Ministry", "body": "MOF", "policy_type": "fiscal_budget", "phase": "phase_1"},
    "sebi": {"label": "SEBI Intelligence", "body": "SEBI", "policy_type": "securities_regulation", "phase": "phase_1"},
    "gst": {"label": "GST Council", "body": "GST_COUNCIL", "policy_type": "tax_gst", "phase": "phase_1"},
    "pli": {"label": "PLI schemes", "body": "DPIIT", "policy_type": "pli_industrial", "phase": "phase_1"},
    "trade": {"label": "Import / export duties", "body": "MOC", "policy_type": "trade", "phase": "phase_1"},
    "mca": {"label": "MCA Intelligence", "body": "MCA", "policy_type": "corporate_law", "phase": "extensible"},
    "industry": {"label": "Industry Regulation", "body": "GOI", "policy_type": "industry_regulation", "phase": "extensible"},
    "state": {"label": "State Government Framework", "body": "GOI", "policy_type": "state_policy", "phase": "extensible"},
}


def list_domain_ids(*, phase: str = "phase_1") -> list[str]:
    if phase == "phase_1":
        return list(PHASE_1_DOMAINS)
    if phase == "extensible":
        return list(PHASE_2_EXTENSIBLE_DOMAINS)
    return list(DOMAIN_INDEX.keys())
