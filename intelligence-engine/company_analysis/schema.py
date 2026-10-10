"""Company Analysis Engine schema constants."""

from __future__ import annotations

COMPANY_ANALYSIS_VERSION = "company-analysis-v1.0.0"
PROGRAMME = "AGI_COMPANY_ANALYSIS"
PROGRAMME_SHORT = "Company Analysis Engine"

# Context Assembly already owns CAE / cae in this codebase.
# This programme uses COMPANY_ANALYSIS; subflags match the brief (CAE_FINANCIAL…).

SECTOR_CONCEPT_LENSES: dict[str, tuple[str, ...]] = {
    "banks": (
        "roe",
        "nim",
        "casa",
        "credit cost",
        "provision",
        "loan growth",
        "leverage",
        "capital adequacy",
        "cet1",
        "gnpa",
        "deposit",
    ),
    "banking": (
        "roe",
        "nim",
        "casa",
        "credit cost",
        "provision",
        "loan growth",
        "leverage",
        "capital adequacy",
        "gnpa",
    ),
    "fmcg": (
        "brand",
        "pricing",
        "working capital",
        "cash conversion",
        "roic",
        "moat",
        "volume",
        "distribution",
        "advertising",
    ),
    "consumer_staples": (
        "brand",
        "pricing",
        "working capital",
        "cash conversion",
        "roic",
        "moat",
    ),
    "it_services": (
        "utilisation",
        "deal",
        "pricing",
        "attrition",
        "offshore",
        "margin",
    ),
    "pharma": ("pipeline", "pricing", "margin", "regulation", "roic"),
    "energy": ("commodity", "capex", "cash flow", "leverage", "regulation"),
    "insurance": ("embedded value", "solvency", "persistency", "combined ratio"),
}

TICKER_PEERS: dict[str, tuple[str, ...]] = {
    "HDFCBANK": ("ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK"),
    "NESTLEIND": ("BRITANNIA", "HINDUNILVR", "TATACONSUM", "GCPL"),
    "INFY": ("TCS", "WIPRO", "HCLTECH", "TECHM"),
    "TCS": ("INFY", "WIPRO", "HCLTECH"),
    "ASIANPAINT": ("BERGEPAINT", "KANSAINER", "AKZOINDIA"),
}

TICKER_BUSINESS: dict[str, dict[str, str]] = {
    "HDFCBANK": {
        "business_model": "Diversified private-sector bank — retail/wholesale lending funded by deposits and wholesale liabilities.",
        "geography": "India (pan-India branch + digital franchise)",
        "products": "Retail loans, wholesale credit, cards, payments, treasury",
        "customers": "Retail depositors, affluent/retail borrowers, corporates",
        "brands": "HDFC Bank",
    },
    "NESTLEIND": {
        "business_model": "Premium packaged foods / staples — brand-led pricing power with distribution depth.",
        "geography": "India",
        "products": "Dairy, prepared dishes, confectionery, beverages, nutrition",
        "customers": "Household consumers via modern + general trade",
        "brands": "Nestlé, Maggi, KitKat, Cerelac, Nescafé",
    },
    "INFY": {
        "business_model": "Global IT services — utilisation-led delivery with large-deal and digital mix.",
        "geography": "Global (India delivery + overseas clients)",
        "products": "Application development, digital, consulting, outsourcing",
        "customers": "Global enterprises across BFSI, retail, manufacturing",
        "brands": "Infosys",
    },
}
