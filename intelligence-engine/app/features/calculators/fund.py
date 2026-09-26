"""Shared FUND_ PIT feature builders (WBS FEAT-005) — E02/E13 consume these."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.models import FeatureMetadata, FeatureValue


class _FundMetric(FeatureCalculator):
    def __init__(self, meta: FeatureMetadata, metric_key: str) -> None:
        self.metadata = meta
        self.metric_key = metric_key

    def compute(
        self,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        available_at: datetime,
        ctx: FeatureContext,
        dep_values: dict[str, FeatureValue],
    ) -> FeatureValue:
        fundamentals = ctx.get("fundamentals") or {}
        raw = fundamentals.get(self.metric_key)
        value = None if raw is None else float(raw)
        # PIT: context must only include fundamentals available_at <= as_of (enforced by service)
        return FeatureValue(
            feature_id=self.metadata.feature_id,
            formula_version=self.metadata.formula_version,
            symbol=symbol,
            as_of=as_of,
            available_at=available_at,
            value=value,
            confidence=self.metadata.confidence if value is not None else 0.0,
            quality_flag="ok" if value is not None else "missing",
            source=self.metadata.source,
            metadata={"metric_key": self.metric_key},
        )


def register_fund_calculators(service: Any) -> None:
    specs = [
        ("FUND_ROE", "roe", "Return on equity"),
        ("FUND_ROIC", "roic", "Return on invested capital"),
        ("FUND_ROCE", "roce", "Return on capital employed"),
        ("FUND_GROSS_MARGIN", "grossMargin", "Gross margin"),
        ("FUND_OPERATING_MARGIN", "operatingMargin", "Operating margin"),
        ("FUND_NET_MARGIN", "netMargin", "Net margin"),
        ("FUND_REVENUE_GROWTH", "revenueGrowth", "Revenue growth"),
        ("FUND_EPS_GROWTH", "epsGrowth", "EPS growth"),
        ("FUND_DEBT_EQUITY", "debtEquity", "Debt to equity"),
        ("FUND_INTEREST_COVERAGE", "interestCoverage", "Interest coverage"),
        ("FUND_FCF_YIELD", "fcfYield", "Free cash flow yield"),
        ("FUND_FCF_CONVERSION", "fcfConversion", "FCF conversion"),
        ("FUND_EP", "earningsYield", "Earnings yield"),
        ("FUND_BP", "bookYield", "Book yield"),
        ("FUND_PEG", "pegRatio", "PEG ratio"),
    ]
    for feature_id, key, desc in specs:
        service.register_calculator(
            _FundMetric(
                FeatureMetadata(
                    feature_id=feature_id,
                    category="FUND_",
                    description=desc,
                    owner="feature-registry",
                    formula_version="1.0.0",
                    dependencies=[],
                    inputs=[f"fundamental.{key}"],
                    refresh_frequency="1d",
                    source="feature_registry",
                    confidence=0.9,
                ),
                key,
            )
        )
