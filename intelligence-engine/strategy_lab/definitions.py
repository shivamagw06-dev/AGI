"""Versioned, claim-safe definitions for every Hedge Fund Lab strategy."""

from __future__ import annotations

from typing import Any

from strategy_lab.contracts import StrategyDefinition


DEFAULT_UNIVERSE = {
    "id": "nse_investable_equities_pit",
    "membership": "effective-dated",
    "include_delisted": True,
    "filters": {
        "listing_status": "tradable_on_signal_date",
        "min_price_inr": 20.0,
        "min_median_adv_inr": 10_000_000.0,
        "history_sessions": 252,
    },
}

DEFAULT_RISK = {
    "max_position_weight": 0.05,
    "max_sector_weight": 0.25,
    "max_adv_participation": 0.05,
    "max_gross_exposure": 1.0,
    "max_net_exposure": 1.0,
    "block_missing_price": True,
    "block_missing_unit": True,
}

DEFAULT_COST = {
    "model": "india_cash_equity_research_v1",
    "schedule_required_at_run_time": True,
    "include": ["brokerage", "exchange", "stt", "gst", "sebi", "stamp", "spread", "impact"],
}

DEFAULT_SLIPPAGE = {
    "model": "participation_square_root_v1",
    "minimum_half_spread_bps": 5.0,
    "adv_participation_cap": 0.05,
}


def _make(
    strategy_id: str,
    name: str,
    role: str,
    description: str,
    features: tuple[str, ...],
    signal: dict[str, Any],
    *,
    entry: dict[str, Any],
    exit: dict[str, Any],
    rebalance: str,
    holding: str,
    benchmark: str = "NIFTY_500_TOTAL_RETURN",
    risk: dict[str, Any] | None = None,
    event_policy: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> StrategyDefinition:
    version = int(strategy_id.rsplit("_v", 1)[1])
    return StrategyDefinition(
        strategy_id=strategy_id,
        strategy_name=name,
        version=version,
        owner="AGI Investment Research",
        description=description,
        role=role,
        universe_definition=DEFAULT_UNIVERSE,
        signal_definition=signal,
        feature_dependencies=features,
        information_cutoff="available_from <= signal_timestamp",
        signal_timestamp="configured_exchange_close_or_explicit_intraday_timestamp",
        entry_rule=entry,
        exit_rule=exit,
        rebalance_frequency=rebalance,
        holding_period=holding,
        benchmark=benchmark,
        risk_constraints={**DEFAULT_RISK, **(risk or {})},
        transaction_cost_model=DEFAULT_COST,
        slippage_model=DEFAULT_SLIPPAGE,
        event_policy=event_policy or {"mode": "observe", "block_material_unresolved_events": False},
        parameters=parameters or {},
    )


_DEFINITIONS = (
    _make(
        "relative_value_v1", "Relative Value V1", "factor_research",
        "Tests valuation discount as a forward-return factor; it does not claim intrinsic value.",
        ("pe", "pb", "ev_ebitda", "fcf_yield", "sector_relative_value"),
        {"formula": "mean(winsorized sector-neutral ranks of earnings_yield, fcf_yield, inverse_pb)", "direction": "higher_is_cheaper"},
        entry={"rule": "top_decile", "execution": "next_session_close"},
        exit={"rule": "rebalance_or_universe_exit"}, rebalance="monthly", holding="6-12 months",
    ),
    _make(
        "quality_v1", "Quality V1", "factor_research",
        "Tests whether durable profitability, cash conversion and balance-sheet strength predict excess return.",
        ("roe", "roic", "roa", "gross_margin", "fcf_margin", "cash_conversion", "debt_ebitda", "interest_coverage"),
        {"formula": "equal-weight sector-neutral quality ranks with leverage inverted", "direction": "higher_is_better"},
        entry={"rule": "top_decile", "execution": "next_session_close"},
        exit={"rule": "rebalance_or_data_invalidation"}, rebalance="quarterly", holding="12 months",
    ),
    _make(
        "value_quality_v1", "Value plus Quality V1", "factor_combination_research",
        "Tests a fixed, pre-registered combination only after standalone value and quality evidence exists.",
        ("relative_value_score", "quality_score"),
        {"formula": "0.5 * relative_value_score + 0.5 * quality_score", "weights": {"value": 0.5, "quality": 0.5}},
        entry={"rule": "top_decile", "execution": "next_session_close"},
        exit={"rule": "rebalance_or_component_invalidation"}, rebalance="monthly", holding="6-12 months",
        parameters={"optimization": "none", "prerequisites": ["relative_value_v1", "quality_v1"]},
    ),
    _make(
        "momentum_v1", "Momentum V1", "factor_and_live_alpha_research",
        "Cross-sectional residual momentum with the most recent month skipped.",
        ("return_1m", "return_6m", "return_12m", "residual_momentum", "volatility", "liquidity"),
        {"formula": "sector-neutral rank(12m_return - 1m_return), volatility scaled", "direction": "higher_is_stronger"},
        entry={"rule": "top_decile", "execution": "next_session_close"},
        exit={"rule": "monthly_rebalance_or_trend_break"}, rebalance="monthly", holding="1-6 months",
    ),
    _make(
        "sector_rotation_v1", "Sector Rotation V1", "cross_sectional_factor_research",
        "Ranks point-in-time sectors on medium-term relative strength without forecasting certainty.",
        ("sector_return_1m", "sector_return_3m", "sector_return_6m", "sector_volatility", "market_regime"),
        {"formula": "rank(0.2*r1m + 0.3*r3m + 0.5*r6m) / volatility", "direction": "higher_is_stronger"},
        entry={"rule": "top_sector_quartile", "execution": "next_session_close"},
        exit={"rule": "monthly_rebalance"}, rebalance="monthly", holding="1-3 months",
        benchmark="NIFTY_500_TOTAL_RETURN",
    ),
    _make(
        "growth_v1", "Growth V1", "factor_research",
        "Tests point-in-time revenue, earnings and free-cash-flow acceleration.",
        ("revenue_growth", "ebitda_growth", "eps_growth", "fcf_growth", "margin_change"),
        {"formula": "sector-neutral robust rank of growth and acceleration", "direction": "higher_is_better"},
        entry={"rule": "top_decile", "execution": "next_session_close"},
        exit={"rule": "quarterly_rebalance_or_revision_reversal"}, rebalance="quarterly", holding="6-12 months",
    ),
    _make(
        "consensus_revisions_v1", "Consensus Revisions V1", "revision_expectation_factor",
        "Uses estimate revision velocity and price response, not target-price upside as expected return.",
        ("eps_revision_30d", "eps_revision_90d", "target_revision_30d", "price_reaction_to_revision", "analyst_coverage"),
        {"formula": "revision velocity minus contemporaneous price reaction, coverage weighted", "direction": "higher_is_positive_revision"},
        entry={"rule": "top_decile_with_minimum_coverage", "execution": "next_session_close"},
        exit={"rule": "revision_reversal_or_monthly_rebalance"}, rebalance="monthly", holding="1-6 months",
    ),
    _make(
        "stress_v1", "Stress V1", "risk_detector",
        "Detects deterioration and tail risk; it is not represented as a standalone alpha strategy.",
        ("drawdown", "volatility", "debt_ebitda", "interest_coverage", "liquidity", "event_severity"),
        {"formula": "robust composite of market, balance-sheet, liquidity and event stress", "direction": "higher_is_more_stressed"},
        entry={"rule": "no_trade_risk_flag"}, exit={"rule": "stress_normalizes"}, rebalance="daily", holding="risk horizon",
        risk={"max_position_weight": 0.0},
    ),
    _make(
        "multi_factor_v1", "Multi-factor V1", "future_portfolio_model",
        "Fixed pre-registered combination evaluated only after every standalone factor has incremental evidence.",
        ("relative_value_score", "quality_score", "growth_score", "momentum_score", "consensus_revision_score"),
        {"formula": "equal-weight orthogonalized factor scores", "optimization": "forbidden_in_v1"},
        entry={"rule": "portfolio_constructor", "execution": "next_session_close"},
        exit={"rule": "scheduled_rebalance_or_risk_breach"}, rebalance="monthly", holding="1-12 months",
        parameters={"weights": {"value": 0.2, "quality": 0.2, "growth": 0.2, "momentum": 0.2, "revisions": 0.2}},
    ),
    _make(
        "mean_reversion_v1", "Mean Reversion V1", "event_conditioned_intraday_research",
        "Tests residual shock reversal only after material-event checks.",
        ("residual_return", "intraday_zscore", "volume_anomaly", "spread_bps", "event_severity"),
        {"formula": "negative residual-return z-score with liquidity and event gates", "direction": "lower_is_long_candidate"},
        entry={"rule": "zscore_below_threshold_and_event_clear", "execution": "simulated_next_quote"},
        exit={"rule": "mean_cross_or_time_stop"}, rebalance="event driven", holding="5-240 minutes",
        event_policy={"mode": "block", "block": ["earnings", "guidance", "regulatory", "credit", "corporate_action"]},
    ),
    _make(
        "opening_range_v1", "Opening Range V1", "intraday_research",
        "Tests opening-range continuation under explicit latency, spread and partial-fill assumptions.",
        ("opening_range_high", "opening_range_low", "vwap", "volume_anomaly", "spread_bps", "realized_volatility"),
        {"formula": "breakout beyond frozen opening range confirmed by relative volume", "direction": "breakout_direction"},
        entry={"rule": "post_range_breakout", "execution": "simulated_next_quote"},
        exit={"rule": "stop_target_or_session_close"}, rebalance="intraday", holding="minutes to session close",
        event_policy={"mode": "label", "block_material_unresolved_events": True},
    ),
    _make(
        "volume_anomaly_v1", "Volume Anomaly V1", "event_detector",
        "Detects unusual participation relative to time-of-day norms without inferring informed direction.",
        ("cumulative_volume_ratio", "relative_volume", "price_return", "trade_imbalance", "event_severity"),
        {"formula": "actual cumulative volume / expected cumulative volume", "direction": "unsigned_event_intensity"},
        entry={"rule": "emit_event_only"}, exit={"rule": "event_expires_at_close"}, rebalance="intraday", holding="event horizon",
        risk={"max_position_weight": 0.0},
    ),
    _make(
        "pairs_v1", "Pairs V1", "research_candidate_generator",
        "Generates pair candidates; no market-neutral claim exists until stationarity, structural-break and borrow tests pass.",
        ("rolling_correlation", "cointegration_pvalue", "spread_zscore", "spread_half_life", "beta", "borrow_cost"),
        {"formula": "cointegration-qualified residual spread z-score", "direction": "two_sided_mean_reversion"},
        entry={"rule": "candidate_only_until_execution_validated"}, exit={"rule": "spread_mean_or_structural_break"},
        rebalance="daily", holding="days to months", benchmark="CASH",
        risk={"max_gross_exposure": 2.0, "max_net_exposure": 0.05},
        event_policy={"mode": "block", "block": ["earnings", "merger", "demerger", "delisting", "borrow_unavailable"]},
    ),
    _make(
        "derivatives_positioning_v1", "Derivatives Positioning V1", "positioning_feature",
        "Describes futures and options positioning; price plus open interest is not treated as predictive by itself.",
        ("futures_basis", "open_interest_change", "option_skew", "iv_term_structure", "put_call_ratio", "participant_positioning"),
        {"formula": "expiry-aware standardized positioning state", "direction": "descriptive"},
        entry={"rule": "feature_only"}, exit={"rule": "feature_expiry"}, rebalance="intraday", holding="feature horizon",
        risk={"max_position_weight": 0.0},
    ),
)


def all_definitions() -> tuple[StrategyDefinition, ...]:
    return _DEFINITIONS


def definition(strategy_id: str) -> StrategyDefinition:
    key = str(strategy_id or "").strip().lower()
    for item in _DEFINITIONS:
        if item.strategy_id == key:
            return item
    raise KeyError(f"unknown_strategy:{strategy_id}")
