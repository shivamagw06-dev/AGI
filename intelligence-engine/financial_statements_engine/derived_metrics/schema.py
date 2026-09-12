"""FSE-07 Derived Metrics Engine contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from financial_statements_engine.util import now_iso

WORKSTREAM_ID = "FSE-07"
VERSION = "1.0.0"
SUBSYSTEM = "derived_metrics_engine"
PROGRAMME = "Financial Statements Engine"
DME_VERSION = "dme-v1.0.0"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "derived_metrics_only_no_buy_sell_never_mutate_warehouse_facts"

METRIC_CONTRACTS = (
    "dcf_metrics.v1",
    "forecast_metrics.v1",
    "screening_metrics.v1",
    "portfolio_metrics.v1",
    "ask_agib_metrics.v1",
    "api_metrics.v1",
)

QUALITY_TARGETS = {
    "calculation_determinism": 1.0,
    "formula_unicity": 1.0,
    "lineage_completeness": 1.0,
    "consumer_consistency": 1.0,
}

CONTRACT_METRIC_SETS: dict[str, tuple[str, ...]] = {
    "dcf_metrics.v1": (
        "free_cash_flow",
        "fcf_margin",
        "roic",
        "nopat",
        "ebit_margin",
        "net_margin",
        "capex_ratio",
        "interest_coverage",
        "net_debt",
    ),
    "forecast_metrics.v1": (
        "gross_margin",
        "ebit_margin",
        "net_margin",
        "asset_turnover",
        "roe",
        "roa",
        "free_cash_flow",
        "fcf_margin",
    ),
    "screening_metrics.v1": (
        "roe",
        "roa",
        "roic",
        "gross_margin",
        "net_margin",
        "current_ratio",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow",
        "accrual_ratio",
    ),
    "portfolio_metrics.v1": (
        "roe",
        "roic",
        "net_margin",
        "free_cash_flow",
        "debt_to_equity",
        "current_ratio",
        "operating_cash_conversion",
    ),
    "ask_agib_metrics.v1": (
        "gross_margin",
        "ebit_margin",
        "net_margin",
        "roe",
        "roa",
        "roic",
        "current_ratio",
        "debt_to_equity",
        "free_cash_flow",
        "fcf_margin",
        "accrual_ratio",
    ),
    "api_metrics.v1": (),  # all calculated metrics
}


def utc_now() -> str:
    return now_iso()


@dataclass
class DerivedMetricRecord:
    metric_id: str
    company_id: str
    ticker: str
    period: str
    metric_name: str
    value: float
    formula_id: str
    formula_version: str
    metric_version: int
    calculation_version: str
    quality_status: str
    source_fact_ids: list[str] = field(default_factory=list)
    lineage_path: list[dict[str, Any]] = field(default_factory=list)
    lineage_reference: str | None = None
    warehouse_version: str | None = None
    validation_version: str | None = None
    quality_reference: str | None = None
    fingerprint: str | None = None
    category: str | None = None
    effective_date: str | None = None
    published_timestamp: str | None = None
    calculation_timestamp: str | None = None
    superseded_by: int | None = None
    dme_version: str = DME_VERSION
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
