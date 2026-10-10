"""CCI-01 — Cross-Company Intelligence constants."""

from __future__ import annotations

CCI_WORKSTREAM_ID = "CCI-01"
CCI_PRODUCT = "Cross-Company Intelligence"
CCI_VERSION = "cci-01-v1.0.0"
CCI_SPEC = "docs/AGI_CCI_01_CROSS_COMPANY_INTELLIGENCE.md"
CCI_ROLE = "relationship_reasoning_over_kg"
RELATIONSHIP_ENGINE_VERSION = "cci-01-rel-v1"
MIN_CONFIDENCE = 0.35

# CCI reasons over KG-01 — never owns or duplicates the graph
GRAPH_SYSTEM_OF_RECORD = "KG-01"
GRAPH_PACKAGE = "institutional_graph"

RELATIONSHIP_TYPES = (
    # Business
    "competitor",
    "supplier",
    "customer",
    "distributor",
    "partner",
    # Ownership
    "parent",
    "subsidiary",
    "cross_holding",
    # Sector
    "same_sector",
    "same_industry",
    "peer_group",
    "index_membership",
    # Macro
    "interest_rates",
    "oil",
    "fx",
    "inflation",
    "gdp",
    "credit_cycle",
    # Portfolio
    "common_holding",
    "common_policy",
    "common_risk",
    "common_committee",
)

RELATIONSHIP_CATEGORIES = (
    "business",
    "ownership",
    "sector",
    "macro",
    "portfolio",
)

TYPE_TO_CATEGORY = {
    "competitor": "business",
    "supplier": "business",
    "customer": "business",
    "distributor": "business",
    "partner": "business",
    "parent": "ownership",
    "subsidiary": "ownership",
    "cross_holding": "ownership",
    "same_sector": "sector",
    "same_industry": "sector",
    "peer_group": "sector",
    "index_membership": "sector",
    "interest_rates": "macro",
    "oil": "macro",
    "fx": "macro",
    "inflation": "macro",
    "gdp": "macro",
    "credit_cycle": "macro",
    "common_holding": "portfolio",
    "common_policy": "portfolio",
    "common_risk": "portfolio",
    "common_committee": "portfolio",
}

# Deterministic ecosystem seeds — not a second graph; relationship discovery priors
ECOSYSTEMS: dict[str, dict[str, object]] = {
    "private_banks": {
        "sector": "Banks",
        "industry": "Private Banks",
        "members": ("HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK"),
        "macro": ("interest_rates", "credit_cycle", "gdp", "inflation"),
        "cluster": "Private Banks",
    },
    "psu_banks": {
        "sector": "Banks",
        "industry": "PSU Banks",
        "members": ("SBIN", "BANKBARODA", "PNB", "CANBK"),
        "macro": ("interest_rates", "credit_cycle", "gdp"),
        "cluster": "PSU Banks",
    },
    "nbfc": {
        "sector": "Financial Services",
        "industry": "NBFC",
        "members": ("BAJFINANCE", "CHOLAFIN", "MFSL", "SUNDARMFIN"),
        "macro": ("interest_rates", "credit_cycle"),
        "cluster": "NBFC",
    },
    "it_services": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "members": ("TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"),
        "macro": ("fx", "gdp", "inflation"),
        "cluster": "IT Services",
    },
    "auto": {
        "sector": "Automobile",
        "industry": "Auto OEMs",
        "members": ("TATAMOTORS", "M&M", "MARUTI", "BAJAJ-AUTO", "HEROMOTOCO"),
        "macro": ("oil", "fx", "gdp", "interest_rates"),
        "cluster": "Auto OEMs",
    },
    "power": {
        "sector": "Utilities",
        "industry": "Power Utilities",
        "members": ("NTPC", "POWERGRID", "TATAPOWER", "ADANIPOWER"),
        "macro": ("oil", "inflation", "gdp"),
        "cluster": "Power Utilities",
    },
    "ports_infra": {
        "sector": "Infrastructure",
        "industry": "Ports",
        "members": ("ADANIPORTS", "GPPL"),
        "macro": ("gdp", "oil", "fx"),
        "cluster": "Ports",
    },
}

MACRO_DRIVERS: dict[str, dict[str, object]] = {
    "interest_rates": {
        "label": "Interest Rates",
        "affects_sectors": ("Banks", "Financial Services", "Automobile", "Real Estate"),
        "affects_clusters": ("Private Banks", "PSU Banks", "NBFC", "Auto OEMs"),
        "channel": "Net Interest Margins / funding cost / demand",
    },
    "oil": {
        "label": "Oil",
        "affects_sectors": ("Automobile", "Utilities", "Infrastructure", "Energy"),
        "affects_clusters": ("Auto OEMs", "Power Utilities", "Ports"),
        "channel": "Input costs / logistics / margins",
    },
    "fx": {
        "label": "FX",
        "affects_sectors": ("Information Technology", "Automobile", "Infrastructure"),
        "affects_clusters": ("IT Services", "Auto OEMs", "Ports"),
        "channel": "Revenue translation / import costs",
    },
    "inflation": {
        "label": "Inflation",
        "affects_sectors": ("Banks", "Information Technology", "Utilities"),
        "affects_clusters": ("Private Banks", "IT Services", "Power Utilities"),
        "channel": "Cost pressure / real rates",
    },
    "gdp": {
        "label": "GDP",
        "affects_sectors": ("Banks", "Automobile", "Infrastructure", "Information Technology"),
        "affects_clusters": ("Private Banks", "Auto OEMs", "Ports", "IT Services"),
        "channel": "Demand cycle",
    },
    "credit_cycle": {
        "label": "Credit Cycle",
        "affects_sectors": ("Banks", "Financial Services"),
        "affects_clusters": ("Private Banks", "PSU Banks", "NBFC"),
        "channel": "Loan growth / asset quality",
    },
}
