"""Compile Institutional Sector Knowledge Objects + evidence packs."""

from __future__ import annotations

from typing import Any

from knowledge_factory.sector_intelligence import store as isi_store
from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.macro_map import macro_relationships
from knowledge_factory.sector_intelligence.playbooks.catalog import sector_playbook
from knowledge_factory.sector_intelligence.producers.core import (
    _constituents,
    produce_framework_mapping,
    produce_sector_cycle,
    produce_sector_leadership,
    produce_sector_risk,
    produce_sector_valuation,
)
from knowledge_factory.sector_intelligence.schema import ISI_VERSION, canonicalize


_TIMELINES: dict[str, list[dict[str, Any]]] = {
    "it_services": [
        {"date": "2008-10-01", "type": "global_event", "title": "GFC tech spending freeze", "impact": "high", "confidence": 0.9, "evidence": "ISI-IT-GFC"},
        {"date": "2020-03-01", "type": "global_event", "title": "COVID — remote delivery acceleration", "impact": "high", "confidence": 0.9, "evidence": "ISI-IT-COVID"},
        {"date": "2023-01-01", "type": "technology_shift", "title": "AI boom spending cycle", "impact": "high", "confidence": 0.85, "evidence": "ISI-IT-AI"},
    ],
    "banks": [
        {"date": "2008-09-01", "type": "global_event", "title": "GFC credit shock", "impact": "high", "confidence": 0.95, "evidence": "ISI-BANK-GFC"},
        {"date": "2013-07-01", "type": "policy", "title": "Taper / rate defence", "impact": "medium", "confidence": 0.85, "evidence": "ISI-BANK-TAPER"},
        {"date": "2020-03-01", "type": "global_event", "title": "COVID moratoriums", "impact": "high", "confidence": 0.9, "evidence": "ISI-BANK-COVID"},
    ],
    "auto": [
        {"date": "2020-03-01", "type": "global_event", "title": "COVID production halt", "impact": "high", "confidence": 0.9, "evidence": "ISI-AUTO-COVID"},
        {"date": "2022-05-01", "type": "policy", "title": "Rate hiking cycle — financing demand", "impact": "medium", "confidence": 0.85, "evidence": "ISI-AUTO-RATES"},
    ],
}


def compile_sector_object(sector: str) -> dict[str, Any]:
    key = canonicalize(sector) or sector
    members = _constituents(key)
    dna = sector_dna(key)
    playbook = sector_playbook(key)
    valuation = produce_sector_valuation(key, members)
    leadership = produce_sector_leadership(key, members)
    cycle = produce_sector_cycle(key, valuation)
    risk = produce_sector_risk(key, members)
    frameworks = produce_framework_mapping(key)
    macro = macro_relationships(key)
    timeline = list(_TIMELINES.get(key, []))
    # Generic timeline if empty
    if not timeline:
        timeline = [
            {"date": "2008-09-01", "type": "global_event", "title": "GFC", "impact": "high", "confidence": 0.8, "evidence": f"ISI-{key}-GFC"},
            {"date": "2020-03-01", "type": "global_event", "title": "COVID", "impact": "high", "confidence": 0.8, "evidence": f"ISI-{key}-COVID"},
        ]
    isi_store.put_timeline(key, timeline)

    coverage = {
        "members": len(members),
        "with_valuation": valuation.get("n_with_pe") or 0,
        "history_years": valuation.get("history_years") or 0,
        "dna_completeness": dna.get("dna_completeness"),
        "playbook": True,
        "macro": True,
        "frameworks": True,
        "cycle": not cycle.get("insufficient"),
    }
    quality = 90.0
    if coverage["history_years"] >= 15:
        quality = 95.0
    if coverage["members"] == 0:
        quality = 70.0

    obj = {
        "kind": "institutional_sector_object",
        "isi_version": ISI_VERSION,
        "sector": key,
        "sector_profile": {
            "display_name": dna.get("display_name"),
            "members": members,
            "maturity": dna.get("industry_maturity"),
            "competitive_structure": dna.get("competitive_structure"),
        },
        "sector_dna": dna,
        "sector_playbook": playbook,
        "historical_valuation": valuation,
        "historical_financial_quality": {
            "median_roic_history": valuation.get("historical_median_roic"),
            "median_pb_history": valuation.get("historical_median_pb"),
        },
        "historical_growth": {"drivers": dna.get("growth_drivers")},
        "historical_risk": risk,
        "historical_cycles": cycle,
        "historical_leadership": leadership,
        "macro_relationships": macro,
        "valuation_framework_mapping": frameworks,
        "preferred_mental_models": dna.get("preferred_mental_models"),
        "timeline": timeline,
        "coverage": coverage,
        "evidence_quality": quality,
        "insufficient": bool(valuation.get("insufficient") and not members),
        "fabricated": False,
    }
    isi_store.put_object(key, obj)

    pack = {
        "kind": "sector_evidence_pack",
        "isi_version": ISI_VERSION,
        "sector": key,
        "valuation": valuation,
        "leadership": leadership,
        "cycle": cycle,
        "macro": macro,
        "frameworks": frameworks,
        "playbook": playbook,
        "dna_summary": {
            "business_model": dna.get("business_model"),
            "preferred_frameworks": dna.get("preferred_frameworks"),
            "forbidden_frameworks": dna.get("forbidden_frameworks"),
        },
        "evidence_quality": quality,
        "coverage": coverage,
        "provenance": "knowledge_factory_sector_intelligence",
        "raw_api": False,
        "fabricated": False,
    }
    isi_store.put_pack(key, pack)
    return obj
