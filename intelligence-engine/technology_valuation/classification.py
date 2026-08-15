"""Authoritative, fail-closed Phase 2A classification."""
from __future__ import annotations
from typing import Any

IT_SERVICES_COHORT = frozenset({"TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"})
_CANONICAL = frozenset({"it_services", "it_consulting", "bpm_digital_services"})
_SOFTWARE_CANONICAL = frozenset({"software", "saas", "software_products", "enterprise_software"})
_PLATFORM_CANONICAL = frozenset({"internet_platform", "internet_platforms", "marketplace", "marketplaces", "digital_marketplace", "digital_platform"})
_CONSUMER_CANONICAL = frozenset({"consumer_internet", "digital_commerce", "ecommerce", "e_commerce", "online_retail", "digital_consumer"})


def classify_technology_subsector(company: dict[str, Any]) -> dict[str, Any]:
    explicit = str(company.get("technology_subsector") or "").strip().upper()
    if explicit == "IT_SERVICES":
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"company_master.technology_subsector"}
    canonical = str(company.get("industry_dna") or company.get("canonical_industry") or "").strip().lower().replace(" ", "_")
    if canonical in _CANONICAL:
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"canonical_industry_taxonomy"}
    if explicit in {"SOFTWARE_PRODUCTS","SAAS","ENTERPRISE_SOFTWARE"}:
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":explicit,"model_family":"SOFTWARE_SAAS","source":"company_master.technology_subsector"}
    if canonical in _SOFTWARE_CANONICAL:
        subsector="SAAS" if canonical=="saas" else "SOFTWARE_PRODUCTS" if canonical in {"software","software_products"} else "ENTERPRISE_SOFTWARE"
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":subsector,"model_family":"SOFTWARE_SAAS","source":"canonical_industry_taxonomy"}
    if explicit in {"INTERNET_PLATFORM","MARKETPLACE","DIGITAL_MARKETPLACE"}:
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":explicit,"model_family":"INTERNET_PLATFORMS_MARKETPLACES","source":"company_master.technology_subsector"}
    if canonical in _PLATFORM_CANONICAL:
        subsector="MARKETPLACE" if "marketplace" in canonical else "INTERNET_PLATFORM"
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":subsector,"model_family":"INTERNET_PLATFORMS_MARKETPLACES","source":"canonical_industry_taxonomy"}
    if explicit in {"CONSUMER_INTERNET","DIGITAL_COMMERCE","ECOMMERCE","ONLINE_RETAIL"}:
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":explicit,"model_family":"CONSUMER_INTERNET_DIGITAL_COMMERCE","source":"company_master.technology_subsector"}
    if canonical in _CONSUMER_CANONICAL:
        subsector="DIGITAL_COMMERCE" if canonical in {"digital_commerce","ecommerce","e_commerce","online_retail"} else "CONSUMER_INTERNET"
        return {"status":"CLASSIFIED","parent_sector":"TECHNOLOGY_AND_DIGITAL","subsector":subsector,"model_family":"CONSUMER_INTERNET_DIGITAL_COMMERCE","source":"canonical_industry_taxonomy"}
    symbol = str(company.get("symbol") or company.get("company_id") or "").strip().upper()
    if symbol in IT_SERVICES_COHORT:
        return {"status":"CLASSIFIED", "parent_sector":"TECHNOLOGY_AND_DIGITAL", "subsector":"IT_SERVICES", "source":"phase_2a_reviewed_cohort_registry"}
    return {"status":"CLASSIFICATION_UNAVAILABLE", "parent_sector":None, "subsector":None,
            "reason":"Authoritative Technology & Digital classification is missing; company-name inference is prohibited."}
