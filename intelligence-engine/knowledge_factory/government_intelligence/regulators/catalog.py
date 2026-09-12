"""Statutory regulators and authorities registry.

Phase 1: RBI, SEBI, GST Council. Others declared for extension.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence.schema import PHASE_1_BODIES

REGULATORS: dict[str, dict[str, Any]] = {
    "RBI": {
        "body_id": "RBI",
        "name": "Reserve Bank of India",
        "kind": "regulator",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": [
            "Monetary policy",
            "Banking regulation",
            "Liquidity management",
            "FX reserves / intervention",
            "Payment systems oversight",
        ],
        "industries_covered": ["banks", "nbfc", "payments", "all_credit"],
        "market_relevance": "Critical",
        "policy_categories": ["monetary", "industry_regulation"],
        "relationships": {"parent": "GOI", "instruments": ["repo", "sdf", "msf", "crr", "slr", "omo", "vrrr"]},
    },
    "SEBI": {
        "body_id": "SEBI",
        "name": "Securities and Exchange Board of India",
        "kind": "regulator",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": [
            "Securities markets regulation",
            "Listing / LODR",
            "Mutual funds / AIF / PMS",
            "Takeovers / buybacks / IPO process",
        ],
        "industries_covered": ["capital_markets", "all_listed"],
        "market_relevance": "Critical",
        "policy_categories": ["securities_regulation"],
        "relationships": {"parent": "GOI"},
    },
    "GST_COUNCIL": {
        "body_id": "GST_COUNCIL",
        "name": "GST Council",
        "kind": "statutory_body",
        "phase": "phase_1",
        "jurisdiction": "India",
        "responsibilities": ["GST rate setting", "Exemptions", "GST law recommendations"],
        "industries_covered": ["all_taxable_goods_services"],
        "market_relevance": "Critical",
        "policy_categories": ["tax_gst"],
        "relationships": {"parent": "GOI", "linked": ["MOF"]},
    },
    # ----- Phase 2+ declared -----
    "MCA": {
        "body_id": "MCA",
        "name": "Ministry of Corporate Affairs",
        "kind": "authority",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Companies Act administration", "Corporate filings"],
        "industries_covered": ["all_companies"],
        "market_relevance": "High",
        "policy_categories": ["corporate_law"],
        "relationships": {"parent": "GOI"},
    },
    "IRDAI": {
        "body_id": "IRDAI",
        "name": "Insurance Regulatory and Development Authority of India",
        "kind": "regulator",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Insurance regulation"],
        "industries_covered": ["insurance"],
        "market_relevance": "High",
        "policy_categories": ["industry_regulation"],
        "relationships": {"parent": "GOI"},
    },
    "TRAI": {
        "body_id": "TRAI",
        "name": "Telecom Regulatory Authority of India",
        "kind": "regulator",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Telecom tariffs / QoS / spectrum policy inputs"],
        "industries_covered": ["telecom"],
        "market_relevance": "High",
        "policy_categories": ["industry_regulation"],
        "relationships": {"parent": "GOI"},
    },
    "CCI": {
        "body_id": "CCI",
        "name": "Competition Commission of India",
        "kind": "statutory_body",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Competition / combination approvals"],
        "industries_covered": ["all"],
        "market_relevance": "High",
        "policy_categories": ["statutory"],
        "relationships": {"parent": "GOI"},
    },
    "NCLT": {
        "body_id": "NCLT",
        "name": "National Company Law Tribunal",
        "kind": "authority",
        "phase": "extensible",
        "jurisdiction": "India",
        "responsibilities": ["Insolvency / company law adjudication"],
        "industries_covered": ["all_companies"],
        "market_relevance": "High",
        "policy_categories": ["corporate_law"],
        "relationships": {"parent": "GOI", "linked": ["MCA"]},
    },
}


def list_regulators(*, phase: str = "phase_1") -> list[dict[str, Any]]:
    rows = []
    for v in REGULATORS.values():
        if phase == "all":
            rows.append(dict(v, fabricated=False, political_opinion=False))
        elif phase == "phase_1" and (
            v.get("phase") == "phase_1" or v.get("body_id") in PHASE_1_BODIES
        ) and v.get("phase") != "extensible":
            rows.append(dict(v, fabricated=False, political_opinion=False))
        elif phase == "extensible" and v.get("phase") == "extensible":
            rows.append(dict(v, fabricated=False, political_opinion=False))
    return rows
