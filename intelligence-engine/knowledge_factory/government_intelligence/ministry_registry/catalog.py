"""Government of India — Ministries / Departments registry.

Phase 1 loads only high-impact bodies. Others remain declared for extension.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.schema import PHASE_1_BODIES

MINISTRIES: dict[str, dict[str, Any]] = {
    "GOI": {
        "body_id": "GOI",
        "name": "Government of India",
        "kind": "government",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["Union governance", "Fiscal policy", "Industrial policy"],
        "industries_covered": ["all"],
        "market_relevance": "Critical",
        "policy_categories": ["fiscal_budget", "pli_industrial", "trade", "tax_gst"],
        "relationships": {"regulators": ["RBI", "SEBI", "GST_COUNCIL"], "parent": None},
    },
    "MOF": {
        "body_id": "MOF",
        "name": "Ministry of Finance",
        "kind": "ministry",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["Union Budget", "Taxation", "Financial sector oversight liaison"],
        "industries_covered": ["banks", "nbfc", "insurance", "capital_markets", "all"],
        "market_relevance": "Critical",
        "policy_categories": ["fiscal_budget", "tax_gst"],
        "relationships": {"parent": "GOI", "regulators": ["RBI", "SEBI"]},
    },
    "DPIIT": {
        "body_id": "DPIIT",
        "name": "Department for Promotion of Industry and Internal Trade",
        "kind": "department",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["PLI schemes", "Industrial policy", "FDI policy administration"],
        "industries_covered": ["electronics", "auto", "pharma", "textiles", "manufacturing"],
        "market_relevance": "High",
        "policy_categories": ["pli_industrial"],
        "relationships": {"parent": "GOI"},
    },
    "MEITY": {
        "body_id": "MEITY",
        "name": "Ministry of Electronics and Information Technology",
        "kind": "ministry",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["Electronics manufacturing", "Semiconductor mission", "IT policy"],
        "industries_covered": ["electronics", "semiconductors", "it_services"],
        "market_relevance": "High",
        "policy_categories": ["pli_industrial"],
        "relationships": {"parent": "GOI"},
    },
    "MOC": {
        "body_id": "MOC",
        "name": "Ministry of Commerce and Industry",
        "kind": "ministry",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["Trade policy", "Import/export duties context", "FTAs", "Export promotion"],
        "industries_covered": ["export_oriented", "metals", "chemicals", "textiles"],
        "market_relevance": "High",
        "policy_categories": ["trade"],
        "relationships": {"parent": "GOI"},
    },
    # ----- Phase 2+ declared (not loaded into Phase 1 active registry) -----
    "MOHFW": {
        "body_id": "MOHFW",
        "name": "Ministry of Health and Family Welfare",
        "kind": "ministry",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Healthcare regulation", "Pharma policy liaison"],
        "industries_covered": ["healthcare", "pharma"],
        "market_relevance": "High",
        "policy_categories": ["industry_regulation"],
        "relationships": {"parent": "GOI"},
    },
    "MOP": {
        "body_id": "MOP",
        "name": "Ministry of Power",
        "kind": "ministry",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Power sector policy", "Renewables coordination"],
        "industries_covered": ["utilities", "power"],
        "market_relevance": "High",
        "policy_categories": ["industry_regulation"],
        "relationships": {"parent": "GOI"},
    },
}


def list_ministries(*, phase: str = "phase_1") -> list[dict[str, Any]]:
    rows = []
    for v in MINISTRIES.values():
        if phase == "all" or v.get("phase") == phase or (
            phase == "phase_1" and v.get("body_id") in PHASE_1_BODIES
        ):
            if phase == "phase_1" and v.get("phase") == "extensible":
                continue
            rows.append(dict(v, fabricated=False, political_opinion=False))
    return rows
