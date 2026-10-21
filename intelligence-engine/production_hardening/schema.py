"""Production Hardening — scalability, observability, regression, data quality, performance."""

from __future__ import annotations

ENGINE_CODE = "production_hardening"
ENGINE_NAME = "Production Hardening"
VERSION = "p6x-production-hardening-v1.0.0"
PROGRAMME = "AGIB_PRODUCTION_HARDENING"
WORKSTREAM_ID = "P6.X"
MILESTONE = "post_p6_hardening"

# Gold-standard regression companies (stable deterministic fingerprints)
GOLD_REGRESSION_UNIVERSE = (
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "NTPC",
    "TATAMOTORS",
)

# Soft freshness SLAs (days) for compiled intelligence layers
FRESHNESS_SLA_DAYS = {
    "company_memory": 7,
    "knowledge_delta": 7,
    "opportunity_intelligence": 3,
    "investment_knowledge_graph": 7,
    "market_context": 1,
}

DATA_SOURCES = (
    "company_memory",
    "knowledge_delta_engine",
    "investment_knowledge_graph",
    "opportunity_intelligence",
    "investment_operations",
    "autonomous_research",
)

SCALE_PRESETS = {
    "smoke": 10,
    "sample_100": 100,
    "nifty500": 500,
    "full": None,  # all symbols from universe file
}

RECOMMENDATION_POLICY = "hardening_diagnostics_only_no_buy_sell"
