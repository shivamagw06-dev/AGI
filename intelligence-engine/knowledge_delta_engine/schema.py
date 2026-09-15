"""P3.1 Knowledge Delta Engine — incremental CompanyMemory compilation."""

from __future__ import annotations

ENGINE_CODE = "knowledge_delta_engine"
ENGINE_NAME = "Knowledge Delta Engine"
VERSION = "p3.1-knowledge-delta-v1.0.0"
PROGRAMME = "AGIB_PHASE3_CONTINUOUSLY_LEARNING_INVESTMENT_OFFICE"
WORKSTREAM_ID = "P3.1"
MILESTONE = "phase_3_1"

DELTA_TYPES = (
    "UNCHANGED",
    "ADDED",
    "UPDATED",
    "REMOVED",
    "SUPERSEDED",
    "CORRECTED",
    "CONFLICT",
)

MEMORY_DELTA_SECTIONS = (
    "financial",
    "ownership",
    "valuation",
    "corporate",
    "sector",
    "market",
    "governance",
    "events",
    "risk",
)

# Fields compared for section diffs (path → label)
COMPARE_PATHS: dict[str, tuple[str, ...]] = {
    "financial": (
        "financial_history.revenue.ttm",
        "financial_history.revenue.yoy",
        "financial_history.revenue.cagr_5y",
        "financial_history.pat.ttm",
        "financial_history.pat.yoy",
        "financial_history.returns.roe",
        "financial_history.returns.roce",
        "financial_history.cash_flow.quality_ocf_to_pat",
        "financial_history.ebitda.margin",
    ),
    "ownership": (
        "ownership_history.latest.promoter",
        "ownership_history.latest.fii",
        "ownership_history.latest.dii",
        "ownership_history.latest.mutual_funds",
        "ownership_history.latest.insurance",
        "ownership_history.latest.pledge",
        "ownership_history.trends.fii.direction",
        "ownership_history.trends.promoter.direction",
    ),
    "valuation": (
        "valuation_history.current.pe",
        "valuation_history.current.pb",
        "valuation_history.current.ev_ebitda",
        "valuation_history.stance",
        "valuation_history.historical_bands.pe.percentile",
        "valuation_history.relative.pe.premium_pct",
    ),
    "corporate": (
        "corporate_history.observations",
        "corporate_history.strategy_evolution",
    ),
    "sector": (
        "sector_history.sector_key",
        "sector_history.pack_id",
    ),
    "market": (
        "price_intelligence.latest_price",
        "price_intelligence.return_1y_pct",
        "price_intelligence.return_5y_pct",
        "price_intelligence.drawdown.max_drawdown_pct",
        "latest_evidence.market.ltp",
    ),
    "governance": (
        "ownership_history.latest.pledge",
        "risk_history.pledge",
        "risk_history.leverage",
    ),
    "events": ("event_timeline.n",),
    "risk": (
        "risk_history.valuation_stretch",
        "risk_history.drawdown.max_drawdown_pct",
        "risk_history.leverage",
    ),
}
