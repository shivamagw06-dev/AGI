"""Canonical point-in-time feature calculations shared by every strategy."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from institutional_warehouse import store
from strategy_lab.contracts import content_hash


@dataclass(frozen=True)
class FeatureSpec:
    feature_id: str
    family: str
    dependencies: tuple[str, ...]
    direction: str
    description: str

    @property
    def definition_hash(self) -> str:
        return content_hash(self.__dict__)


FEATURE_SPECS = {
    spec.feature_id: spec for spec in (
        FeatureSpec("pe", "valuation", ("price", "eps_ttm"), "lower", "Price divided by point-in-time trailing EPS."),
        FeatureSpec("pb", "valuation", ("price", "book_value_per_share"), "lower", "Price divided by book value per share."),
        FeatureSpec("earnings_yield", "valuation", ("eps_ttm", "price"), "higher", "Point-in-time EPS divided by price."),
        FeatureSpec("fcf_yield", "valuation", ("free_cash_flow", "market_cap"), "higher", "Free cash flow divided by market cap."),
        FeatureSpec("roe", "quality", ("net_income", "average_equity"), "higher", "Net income divided by average equity."),
        FeatureSpec("roic", "quality", ("nopat", "invested_capital"), "higher", "NOPAT divided by invested capital."),
        FeatureSpec("roa", "quality", ("net_income", "average_assets"), "higher", "Net income divided by average assets."),
        FeatureSpec("gross_margin", "quality", ("gross_profit", "revenue"), "higher", "Gross profit divided by revenue."),
        FeatureSpec("ebitda_margin", "quality", ("ebitda", "revenue"), "higher", "EBITDA divided by revenue."),
        FeatureSpec("fcf_margin", "quality", ("free_cash_flow", "revenue"), "higher", "Free cash flow divided by revenue."),
        FeatureSpec("cash_conversion", "quality", ("operating_cash_flow", "net_income"), "higher", "Operating cash flow divided by net income."),
        FeatureSpec("debt_ebitda", "quality", ("net_debt", "ebitda"), "lower", "Net debt divided by EBITDA."),
        FeatureSpec("interest_coverage", "quality", ("ebit", "interest_expense"), "higher", "EBIT divided by interest expense."),
        FeatureSpec("revenue_growth", "growth", ("revenue", "revenue_prior"), "higher", "Point-in-time year-over-year revenue growth."),
        FeatureSpec("ebitda_growth", "growth", ("ebitda", "ebitda_prior"), "higher", "Point-in-time year-over-year EBITDA growth."),
        FeatureSpec("eps_growth", "growth", ("eps_ttm", "eps_ttm_prior"), "higher", "Point-in-time year-over-year EPS growth."),
        FeatureSpec("fcf_growth", "growth", ("free_cash_flow", "free_cash_flow_prior"), "higher", "Point-in-time year-over-year FCF growth."),
        FeatureSpec("margin_change", "growth", ("ebitda_margin", "ebitda_margin_prior"), "higher", "Change in EBITDA margin."),
        FeatureSpec("return_1m", "momentum", ("price_history",), "higher", "21-session total return."),
        FeatureSpec("return_3m", "momentum", ("price_history",), "higher", "63-session total return."),
        FeatureSpec("return_6m", "momentum", ("price_history",), "higher", "126-session total return."),
        FeatureSpec("return_12m", "momentum", ("price_history",), "higher", "252-session total return."),
        FeatureSpec("residual_momentum", "momentum", ("return_12m", "return_1m", "sector_return_12m"), "higher", "12-1 momentum net of sector."),
        FeatureSpec("volatility", "risk", ("price_history",), "lower", "Annualized standard deviation of daily total returns."),
        FeatureSpec("drawdown", "risk", ("price_history",), "higher", "Current drawdown from running peak."),
        FeatureSpec("liquidity", "risk", ("price_history", "volume_history"), "higher", "Median traded value."),
        FeatureSpec("beta", "risk", ("price_history", "benchmark_history"), "neutral", "Covariance to benchmark divided by benchmark variance."),
    )
}


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    a, b = _number(numerator), _number(denominator)
    return None if a is None or b in (None, 0.0) else a / b


def _growth(current: Any, prior: Any) -> float | None:
    a, b = _number(current), _number(prior)
    return None if a is None or b in (None, 0.0) else a / abs(b) - 1.0


def _returns(prices: Sequence[float]) -> list[float]:
    return [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices)) if prices[i - 1] > 0]


def _momentum(prices: Sequence[float], sessions: int) -> float | None:
    return None if len(prices) <= sessions or prices[-sessions - 1] <= 0 else prices[-1] / prices[-sessions - 1] - 1.0


def calculate_snapshot(
    company_id: str,
    as_of: str,
    values: Mapping[str, Any],
    *,
    price_history: Sequence[Mapping[str, Any]] = (),
    benchmark_history: Sequence[Mapping[str, Any]] = (),
    lineage: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    prices = [_number(row.get("total_return_index") or row.get("adjusted_close") or row.get("close")) for row in price_history]
    prices = [value for value in prices if value is not None and value > 0]
    volumes = [(_number(row.get("close")) or 0.0) * (_number(row.get("volume")) or 0.0) for row in price_history]
    benchmark = [_number(row.get("total_return_index") or row.get("adjusted_close") or row.get("close")) for row in benchmark_history]
    benchmark = [value for value in benchmark if value is not None and value > 0]
    daily = _returns(prices)
    bench_daily = _returns(benchmark)
    computed: dict[str, float | None] = {
        "pe": _ratio(values.get("price"), values.get("eps_ttm")),
        "pb": _ratio(values.get("price"), values.get("book_value_per_share")),
        "earnings_yield": _ratio(values.get("eps_ttm"), values.get("price")),
        "fcf_yield": _ratio(values.get("free_cash_flow"), values.get("market_cap")),
        "roe": _ratio(values.get("net_income"), values.get("average_equity")),
        "roic": _ratio(values.get("nopat"), values.get("invested_capital")),
        "roa": _ratio(values.get("net_income"), values.get("average_assets")),
        "gross_margin": _ratio(values.get("gross_profit"), values.get("revenue")),
        "ebitda_margin": _ratio(values.get("ebitda"), values.get("revenue")),
        "fcf_margin": _ratio(values.get("free_cash_flow"), values.get("revenue")),
        "cash_conversion": _ratio(values.get("operating_cash_flow"), values.get("net_income")),
        "debt_ebitda": _ratio(values.get("net_debt"), values.get("ebitda")),
        "interest_coverage": _ratio(values.get("ebit"), values.get("interest_expense")),
        "revenue_growth": _growth(values.get("revenue"), values.get("revenue_prior")),
        "ebitda_growth": _growth(values.get("ebitda"), values.get("ebitda_prior")),
        "eps_growth": _growth(values.get("eps_ttm"), values.get("eps_ttm_prior")),
        "fcf_growth": _growth(values.get("free_cash_flow"), values.get("free_cash_flow_prior")),
        "margin_change": None,
        "return_1m": _momentum(prices, 21),
        "return_3m": _momentum(prices, 63),
        "return_6m": _momentum(prices, 126),
        "return_12m": _momentum(prices, 252),
        "residual_momentum": None,
        "volatility": statistics.stdev(daily) * math.sqrt(252.0) if len(daily) > 1 else None,
        "drawdown": prices[-1] / max(prices) - 1.0 if prices else None,
        "liquidity": statistics.median(volumes[-63:]) if volumes else None,
        "beta": None,
    }
    current_margin = computed["ebitda_margin"]
    prior_margin = _ratio(values.get("ebitda_prior"), values.get("revenue_prior"))
    if current_margin is not None and prior_margin is not None:
        computed["margin_change"] = current_margin - prior_margin
    if computed["return_12m"] is not None and computed["return_1m"] is not None:
        computed["residual_momentum"] = computed["return_12m"] - computed["return_1m"] - float(values.get("sector_return_12m") or 0.0)
    if len(daily) > 1 and len(bench_daily) > 1:
        n = min(len(daily), len(bench_daily), 252)
        asset, market = daily[-n:], bench_daily[-n:]
        market_mean = statistics.mean(market)
        variance = sum((value - market_mean) ** 2 for value in market)
        if variance > 0:
            asset_mean = statistics.mean(asset)
            computed["beta"] = sum((asset[i] - asset_mean) * (market[i] - market_mean) for i in range(n)) / variance

    source_hash = content_hash(lineage or {})
    output = []
    for feature_id, value in computed.items():
        if value is None or not math.isfinite(value):
            continue
        spec = FEATURE_SPECS[feature_id]
        output.append({
            "company_id": company_id,
            "feature_id": feature_id,
            "as_of": as_of,
            "value": value,
            "family": spec.family,
            "definition_hash": spec.definition_hash,
            "source_observation_hash": source_hash,
            "available_from": as_of,
            "lineage_json": dict(lineage or {}),
        })
    return output


def persist_features(rows: Iterable[Mapping[str, Any]], *, actor: str = "system") -> dict[str, Any]:
    return store.upsert(
        "canonical_feature_observations", [dict(row) for row in rows], source="canonical_feature_store",
        actor=actor, reason="materialize_point_in_time_features",
    )
