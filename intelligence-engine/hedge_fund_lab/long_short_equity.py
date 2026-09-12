"""Governed Long/Short Equity research foundation.

This module composes existing E13 and Hedge Fund scanner evidence. It does not
create orders, position sizes, or performance claims before the validation and
short-borrow gates are satisfied.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


LIFECYCLE = [
    "candidate",
    "research",
    "ic_review",
    "approved",
    "paper_portfolio",
    "production",
    "monitor",
    "reduce",
    "exit",
]

HORIZONS = {
    "fundamental_strategic": "6-36+ months",
    "fundamental_tactical": "1-6 months",
    "event_driven": "days-months",
    "relative_value": "1-90 days",
}

DATA_FOUNDATION = (
    ("annual_fundamentals", "available", "Master 10Y Capital IQ workbook; INR millions"),
    ("quarterly_fundamentals", "partial", "Warehouse coverage varies by company"),
    ("eod_market_history", "available", "Adjusted daily warehouse history"),
    ("corporate_actions", "available", "Warehouse corporate-action history"),
    ("ownership", "partial", "Promoter and institutional observations; vintages vary"),
    ("consensus_estimates", "partial", "Coverage and historical vintages are incomplete"),
    ("events", "partial", "Announcements exist; normalized catalyst timestamps are incomplete"),
    ("pit_availability_timestamps", "partial", "Some rows lack publication/availability timestamps"),
    ("historical_constituents_delistings", "missing", "Required for survivorship-safe backtests"),
    ("borrow_availability", "missing", "Required before any short becomes trade eligible"),
    ("borrow_fee_history", "missing", "Required for costed short returns"),
    ("short_interest_days_to_cover", "missing", "Required for crowding and squeeze risk"),
    ("utilisation_recall_history", "missing", "Required for short survivability"),
    ("bid_ask_market_impact", "missing", "Required for execution backtests"),
)

PROMOTION_GATES = (
    "point_in_time_data",
    "signal_backtest",
    "portfolio_backtest",
    "execution_backtest",
    "transaction_costs",
    "borrow_costs",
    "liquidity_capacity",
    "factor_risk",
    "walk_forward",
    "out_of_sample",
    "paper_portfolio",
    "independent_approval",
)


def readiness() -> dict[str, Any]:
    data = [
        {"dataset": name, "status": status, "detail": detail}
        for name, status, detail in DATA_FOUNDATION
    ]
    blocking = [row[0] for row in DATA_FOUNDATION if row[1] == "missing"]
    return {
        "ok": True,
        "strategy_id": "long_short_equity",
        "lifecycle": "candidate",
        "health": "degraded" if blocking else "healthy",
        "allowed_use": "research candidate generation only",
        "execution_eligible": False,
        "performance_claims_allowed": False,
        "market_neutral_claim_allowed": False,
        "position_sizing_allowed": False,
        "horizons": HORIZONS,
        "data_foundation": data,
        "blocking_datasets": blocking,
        "promotion_gates": [
            {"gate": gate, "status": "not_validated"}
            for gate in PROMOTION_GATES
        ],
        "lifecycle_states": LIFECYCLE,
        "architecture": {
            "fundamental_scoring": "E13 Equity Fundamental L/S",
            "candidate_scanners": "Hedge Fund Lab warehouse scanners",
            "risk_context": "E14 plus portfolio exposure calculators",
            "reliability_authority": "Reliability Registry",
        },
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def research_book(*, limit: int = 10) -> dict[str, Any]:
    """Return governed research candidates, never a proposed portfolio."""
    from hedge_fund_lab.scanner import scan

    n = max(1, min(int(limit or 10), 25))
    long_scan = scan("alpha", limit=n)
    short_scan = scan("stress", limit=n)
    pair_scan = scan("pairs", limit=n)
    longs = [_long_candidate(row) for row in (long_scan.get("results") or [])]
    shorts = [_short_candidate(row) for row in (short_scan.get("results") or [])]
    pairs = [_pair_candidate(row) for row in (pair_scan.get("results") or [])]
    ready = readiness()
    return {
        "ok": bool(long_scan.get("ok") or short_scan.get("ok") or pair_scan.get("ok")),
        "strategy_id": "long_short_equity",
        "classification": "governed_research_book",
        "long_candidates": longs,
        "short_candidates": shorts,
        "relative_value_candidates": pairs,
        "counts": {"longs": len(longs), "shorts": len(shorts), "pairs": len(pairs)},
        "portfolio": None,
        "portfolio_reason": "Portfolio construction is blocked until every promotion gate passes.",
        "readiness": ready,
        "policy": "Research candidates only; no orders, sizing, fair value, or performance claims.",
    }


def _long_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": row.get("ticker"),
        "company_name": row.get("company_name"),
        "side": "long",
        "state": "candidate",
        "horizon": HORIZONS["fundamental_tactical"],
        "independent_signals": dict(row.get("factor_scores") or {}),
        "screening_priority": row.get("alpha_opportunity_score"),
        "confidence": row.get("coverage"),
        "thesis": row.get("why"),
        "catalyst": None,
        "fair_value": None,
        "invalidation": None,
        "position_size": None,
        "missing_requirements": ["variant perception", "catalyst", "fair value", "invalidation", "risk budget"],
        "execution_eligible": False,
    }


def _short_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": row.get("ticker"),
        "company_name": row.get("company_name"),
        "side": "short",
        "state": "candidate",
        "horizon": HORIZONS["fundamental_tactical"],
        "stress_flags": list(row.get("stress_flags") or []),
        "thesis": row.get("why"),
        "decline_catalyst": None,
        "fair_value": None,
        "invalidation": None,
        "borrow": {
            "available": None,
            "fee": None,
            "utilisation": None,
            "days_to_cover": None,
            "recall_risk": None,
            "squeeze_score": None,
        },
        "position_size": None,
        "missing_requirements": [
            "dedicated short thesis",
            "decline catalyst",
            "fair value",
            "invalidation",
            "borrow availability",
            "borrow fee",
            "crowding and squeeze evidence",
        ],
        "execution_eligible": False,
    }


def _pair_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "state": "candidate",
        "horizon": HORIZONS["relative_value"],
        "market_neutral": False,
        "execution_eligible": False,
    }
