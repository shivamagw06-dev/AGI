"""Company Memory — AGIB Knowledge Compiler schema.

Persistent, company-specific, time-series intelligence — not raw API responses.
Does not modify Decision Engine formulas, gate thresholds, or Constitution.
"""

from __future__ import annotations

ENGINE_CODE = "company_memory"
ENGINE_NAME = "Company Memory Knowledge Compiler"
VERSION = "company-memory-v1.0.0"
PROGRAMME = "AGIB_COMPANY_MEMORY_KNOWLEDGE_COMPILER"
WORKSTREAM_ID = "KC.1"
MILESTONE = "knowledge_compiler_v1"

# Display → resolve (post NSE rename)
TICKER_ALIASES = {
    "TATAMOTORS": "TMPV",
    "ZOMATO": "ETERNAL",
}

IC10_UNIVERSE = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "ETERNAL",
    "TATAMOTORS",
    "SUNPHARMA",
    "NTPC",
    "HAL",
    "ASIANPAINT",
    "ULTRACEMCO",
)

# CompanyMemory sections (long-lived intelligence objects)
MEMORY_SECTIONS = (
    "business_model",
    "competitive_position",
    "financial_history",
    "ownership_history",
    "valuation_history",
    "corporate_history",
    "risk_history",
    "sector_history",
    "event_timeline",
    "price_intelligence",
    "latest_evidence",
)

# NSE / public source → intelligence layer (catalog; not all ingested in v1)
SOURCE_INTELLIGENCE_MAP = {
    "historical_ohlcv": "market_intelligence",
    "shareholding": "ownership_intelligence",
    "financial_results": "financial_intelligence",
    "corporate_announcements": "corporate_intelligence",
    "annual_reports": "strategy_intelligence",
    "board_meetings": "governance_intelligence",
    "bulk_block_deals": "institutional_flow_intelligence",
    "insider_trading": "insider_behaviour_intelligence",
    "corporate_actions": "capital_allocation_intelligence",
    "option_chain": "derivatives_intelligence",
    "futures": "positioning_intelligence",
    "delivery_data": "accumulation_distribution_intelligence",
    "fii_dii_statistics": "market_flow_intelligence",
    "circulars": "regulatory_intelligence",
    "surveillance": "risk_intelligence",
    "ipo_data": "listing_intelligence",
}

# Reference data — do not store as permanent memory
REFERENCE_ONLY = (
    "trading_holidays",
    "market_timings",
    "static_security_master",
    "circular_metadata_without_lasting_relevance",
)

# External public sources for future expansion (catalog)
EXTERNAL_SOURCES = {
    "BSE": {"purpose": "announcements, filings, corporate actions", "access": "public"},
    "SEBI": {"purpose": "insider, SAST, enforcement", "access": "public"},
    "MCA": {"purpose": "directors, charges, statutory filings", "access": "mostly_public"},
    "RBI": {"purpose": "rates, banking system, macro", "access": "public"},
    "AMFI": {"purpose": "MF NAVs, scheme data", "access": "public"},
    "CCIL": {"purpose": "bond / money markets", "access": "partial"},
    "MOSPI": {"purpose": "GDP, CPI, IIP", "access": "public"},
    "COMPANY_IR": {"purpose": "AR, presentations, transcripts", "access": "public_summarise_not_republish"},
}

SECTOR_KPI_KEYS = {
    "banks": ("CASA", "NIM", "GNPA", "NNPA", "PCR", "CET1", "Deposit_Growth", "Credit_Growth"),
    "it_services": ("Utilisation", "Attrition", "Deal_TCV", "EBIT_Margin", "AI_Revenue"),
    "pharma": ("US_Exposure", "ANDA", "FDA_Inspections", "Product_Launches"),
    "cement": ("Capacity", "Utilisation", "Fuel_Cost", "Realisation"),
    "power": ("PLF", "Generation_Mix", "Capex", "Regulated_Equity"),
    "auto": ("Volumes", "EV_Mix", "Exports", "ASPs"),
    "paints": ("Decorative_Volume", "Realisation", "Gross_Margin"),
    "defence": ("Order_Book", "Execution", "Indigenisation"),
    "energy_conglomerate": ("Refining", "Petchem", "Retail", "Upstream"),
    "consumer_internet": ("GMV", "Take_Rate", "Contribution_Margin"),
}
