"""Configuration-driven IIE taxonomies — no company-specific hardcoding in engines."""

from __future__ import annotations

DNA_DIMENSIONS: list[str] = [
    "business_quality",
    "moat",
    "execution_quality",
    "innovation",
    "capital_discipline",
    "management_credibility",
    "balance_sheet_quality",
    "industry_leadership",
    "scalability",
    "margin_durability",
    "pricing_power",
    "resilience",
    "commodity_sensitivity",
    "interest_rate_sensitivity",
    "currency_sensitivity",
    "government_dependency",
    "customer_concentration",
    "supplier_risk",
]

SECTOR_CATALOG: list[dict[str, str]] = [
    {"sector_id": "banking", "label": "Banking"},
    {"sector_id": "it_services", "label": "IT Services"},
    {"sector_id": "power", "label": "Power"},
    {"sector_id": "capital_goods", "label": "Capital Goods"},
    {"sector_id": "healthcare", "label": "Healthcare"},
    {"sector_id": "automobiles", "label": "Automobiles"},
    {"sector_id": "consumer_staples", "label": "Consumer Staples"},
    {"sector_id": "real_estate", "label": "Real Estate"},
    {"sector_id": "telecommunications", "label": "Telecommunications"},
    {"sector_id": "metals", "label": "Metals"},
    {"sector_id": "chemicals", "label": "Chemicals"},
    {"sector_id": "infrastructure", "label": "Infrastructure"},
    {"sector_id": "ems", "label": "EMS"},
    {"sector_id": "renewables", "label": "Renewables"},
    {"sector_id": "defence", "label": "Defence"},
    {"sector_id": "railways", "label": "Railways"},
    {"sector_id": "financial_services", "label": "Financial Services"},
    {"sector_id": "energy", "label": "Energy"},
    {"sector_id": "retail", "label": "Retail"},
    {"sector_id": "pharma", "label": "Healthcare"},
    {"sector_id": "fmcg", "label": "Consumer Staples"},
    {"sector_id": "auto", "label": "Automobiles"},
    {"sector_id": "telecom", "label": "Telecommunications"},
]

THEME_CATALOG: list[dict] = [
    {"theme_id": "artificial_intelligence", "label": "Artificial Intelligence", "keywords": ["ai", "genai", "artificial intelligence"]},
    {"theme_id": "semiconductors", "label": "Semiconductors", "keywords": ["semiconductor", "chip"]},
    {"theme_id": "defence", "label": "Defence", "keywords": ["defence", "defense", "military"]},
    {"theme_id": "renewables", "label": "Renewables", "keywords": ["renewable", "solar", "wind", "green energy"]},
    {"theme_id": "ev", "label": "EV", "keywords": ["ev", "electric vehicle", "battery"]},
    {"theme_id": "data_centres", "label": "Data Centres", "keywords": ["data centre", "data center", "hyperscale"]},
    {"theme_id": "manufacturing", "label": "Manufacturing", "keywords": ["manufacturing", "pli", "factory"]},
    {"theme_id": "china_plus_one", "label": "China+1", "keywords": ["china+1", "china plus one", "supply chain"]},
    {"theme_id": "infrastructure", "label": "Infrastructure", "keywords": ["infrastructure", "infra"]},
    {"theme_id": "railways", "label": "Railways", "keywords": ["railway", "rail"]},
    {"theme_id": "power", "label": "Power", "keywords": ["power", "electricity", "transmission"]},
    {"theme_id": "water", "label": "Water", "keywords": ["water", "wastewater"]},
    {"theme_id": "housing", "label": "Housing", "keywords": ["housing", "real estate", "residential"]},
    {"theme_id": "digital_payments", "label": "Digital Payments", "keywords": ["upi", "payments", "fintech"]},
    {"theme_id": "healthcare", "label": "Healthcare", "keywords": ["pharma", "hospital", "healthcare"]},
    {"theme_id": "capital_goods", "label": "Capital Goods", "keywords": ["capex", "capital goods", "engineering"]},
]

# Macro event → affected sector chain (direct + indirect)
MACRO_IMPACT_MAP: dict[str, list[str]] = {
    "repo_rate_cut": [
        "banking",
        "financial_services",
        "real_estate",
        "infrastructure",
        "capital_goods",
        "chemicals",
        "retail",
    ],
    "repo_rate_hike": ["banking", "financial_services", "real_estate", "auto"],
    "oil_spike": ["energy", "auto", "chemicals", "aviation"],
    "inr_depreciation": ["it_services", "pharma", "metals", "auto"],
    "gdp_acceleration": ["capital_goods", "banking", "auto", "fmcg", "real_estate"],
    "fiscal_capex": ["capital_goods", "infrastructure", "power", "defence", "railways"],
}

MONITOR_METRICS: list[str] = [
    "revenue_growth",
    "margins",
    "order_book",
    "capacity",
    "promoter_holding",
    "debt",
    "capex",
    "management_guidance",
    "large_contracts",
    "product_launches",
    "market_share",
    "commodity_costs",
    "fx",
    "interest_rates",
    "government_policy",
    "board_changes",
    "litigation",
    "ratings",
]

# Fact-key → intelligence mapping hints
FACT_TO_INTEL: dict[str, list[str]] = {
    "guidance": ["catalysts", "growth_outlook", "monitoring"],
    "risks": ["risks", "bear_thesis"],
    "opportunities": ["opportunities", "bull_thesis"],
    "margins": ["profitability", "operating_leverage", "monitoring"],
    "capex": ["capital_allocation", "capital_requirements", "monitoring"],
    "debt": ["balance_sheet_strength", "financial_risks", "monitoring"],
    "shareholding": ["ownership_trends", "governance", "monitoring"],
    "business_model": ["business_summary", "moat"],
    "products": ["product_mix", "competitive_landscape"],
    "revenue": ["financial_strength", "growth_outlook"],
    "pat": ["profitability", "financial_strength"],
    "management": ["management_quality", "governance"],
    "board": ["governance", "monitoring"],
}

MIN_EVIDENCE_CONFIDENCE = 0.45
PREFERRED_STATUSES = {"verified", "pending"}  # never raw docs; prefer verified
