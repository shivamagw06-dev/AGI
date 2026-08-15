"""Authoritative, fail-closed Phase 2A classification."""
from __future__ import annotations
from typing import Any

IT_SERVICES_COHORT = frozenset({"TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"})
_CANONICAL = frozenset({"it_services", "it_consulting", "bpm_digital_services"})


def classify_technology_subsector(company: dict[str, Any]) -> dict[str, Any]:
    explicit = str(company.get("technology_subsector") or "").strip().upper()
    if explicit == "IT_SERVICES":
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"company_master.technology_subsector"}
    canonical = str(company.get("industry_dna") or company.get("canonical_industry") or "").strip().lower().replace(" ", "_")
    if canonical in _CANONICAL:
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"canonical_industry_taxonomy"}
    symbol = str(company.get("symbol") or company.get("company_id") or "").strip().upper()
    if symbol in IT_SERVICES_COHORT:
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"phase_2a_reviewed_cohort_registry"}
    return {"status":"CLASSIFICATION_UNAVAILABLE", "parent_sector":None, "subsector":None,
            "reason":"Authoritative Technology & Digital classification is missing; company-name inference is prohibited."}
