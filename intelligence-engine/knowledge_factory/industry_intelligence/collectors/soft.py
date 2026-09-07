"""Soft collectors — registry + Sector DNA + Government/Macro soft links. Never fabricate."""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence.playbooks.catalog import get_playbook
from knowledge_factory.industry_intelligence.registry.catalog import (
    INDUSTRY_REGISTRY,
    build_company_industry_map,
)


def _sector_dna(sector: str) -> dict[str, Any]:
    try:
        from knowledge_factory.sector_intelligence.dna.catalog import sector_dna

        return dict(sector_dna(sector) or {})
    except Exception:
        return {}


def _gov_domains_for(industry_id: str) -> list[str]:
    """Soft-read Government Intelligence domain ids relevant to industry (references only)."""
    try:
        from knowledge_factory.government_intelligence import store as igri_store
        from knowledge_factory.government_intelligence.schema import PHASE_1_DOMAINS

        if igri_store.policy_count() == 0:
            return list(PHASE_1_DOMAINS)
        # Reference domains present — do not duplicate policy bodies
        domains = sorted({str(p.get("domain") or "") for p in igri_store.list_policies()})
        return domains or list(PHASE_1_DOMAINS)
    except Exception:
        return ["rbi", "budget", "sebi", "gst", "pli", "trade"]


def collect_industry_context(industry_id: str, *, members: list[str] | None = None) -> dict[str, Any]:
    iid = str(industry_id or "").lower()
    meta = dict(INDUSTRY_REGISTRY.get(iid) or {})
    sector = meta.get("sector") or iid
    return {
        "industry_id": iid,
        "meta": meta,
        "sector": sector,
        "dna": _sector_dna(sector),
        "playbook": get_playbook(iid),
        "members": list(members or []),
        "government_domains": _gov_domains_for(iid),
        "company_map_size": len(build_company_industry_map()),
        "sources_priority": [
            "annual_reports",
            "investor_presentations",
            "company_websites",
            "nse",
            "bse",
            "ministry_publications",
            "rbi",
            "sebi",
            "government_reports",
            "industry_associations",
            "institutional_sector_dna",
            "institutional_industry_playbook",
        ],
    }
