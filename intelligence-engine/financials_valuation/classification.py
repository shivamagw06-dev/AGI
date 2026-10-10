"""Authoritative financial-subsector classification; fail closed."""
from __future__ import annotations
from typing import Any
from financials_valuation.schema import SUBSECTORS

_AUTHORITATIVE = {
    "banks": "COMMERCIAL_BANK", "commercial_bank": "COMMERCIAL_BANK",
    "small_finance_bank": "SMALL_FINANCE_BANK", "payments_bank": "PAYMENTS_BANK",
    "nbfc": "NBFC", "housing_finance": "HOUSING_FINANCE", "hfc": "HOUSING_FINANCE",
    "life_insurance": "LIFE_INSURANCE", "general_insurance": "GENERAL_INSURANCE",
    "health_insurance": "HEALTH_INSURANCE", "asset_management": "ASSET_MANAGEMENT",
    "broker": "BROKER", "stock_broker": "BROKER", "exchange": "EXCHANGE_INFRASTRUCTURE",
    "fintech_payments": "FINTECH_PAYMENTS", "diversified_financials": "DIVERSIFIED_FINANCIALS",
}

def classify_financial_subsector(master: dict[str, Any]) -> dict[str, Any]:
    explicit = str(master.get("financial_subsector") or "").upper()
    if explicit in SUBSECTORS:
        return {"status": "CLASSIFIED", "subsector": explicit, "source": "company_master.financial_subsector"}
    dna = str(master.get("industry_dna") or master.get("canonical_industry") or "").lower().replace(" ", "_")
    mapped = _AUTHORITATIVE.get(dna)
    if mapped:
        return {"status": "CLASSIFIED", "subsector": mapped, "source": "canonical_industry_taxonomy"}
    return {"status": "CLASSIFICATION_UNAVAILABLE", "subsector": None,
            "reason": "Authoritative financial subsector is missing; company name inference is prohibited."}
