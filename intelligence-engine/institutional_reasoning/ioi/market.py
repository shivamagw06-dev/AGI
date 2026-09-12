"""Module 2 — Market Outcome Engine.

Collects versioned market outcomes. Suite/tests inject realised paths;
production may soft-consume live quotes without becoming a top-level engine.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

MARKET_VERSION = "market-outcome-v1.0.0"

# Deterministic seed paths for institutional review (not live brokerage).
_SEED_PATHS: dict[str, dict[str, Any]] = {
    "INFY": {
        "entry_price": 1400.0,
        "current_price": 1624.0,
        "total_return": 0.16,
        "benchmark_return": 0.10,
        "sector_return": 0.12,
        "max_drawdown": 0.08,
        "volatility": 0.22,
        "dividends": 0.012,
        "splits": 0.0,
        "corporate_actions": [],
    },
    "TCS": {
        "entry_price": 3200.0,
        "current_price": 3360.0,
        "total_return": 0.05,
        "benchmark_return": 0.10,
        "sector_return": 0.12,
        "max_drawdown": 0.11,
        "volatility": 0.20,
        "dividends": 0.015,
        "splits": 0.0,
        "corporate_actions": [],
    },
    "HDFCBANK": {
        "entry_price": 1450.0,
        "current_price": 1522.0,
        "total_return": 0.05,
        "benchmark_return": 0.10,
        "sector_return": 0.07,
        "max_drawdown": 0.14,
        "volatility": 0.24,
        "dividends": 0.008,
        "splits": 0.0,
        "corporate_actions": [],
    },
    "WIPRO": {
        "entry_price": 450.0,
        "current_price": 414.0,
        "total_return": -0.08,
        "benchmark_return": 0.10,
        "sector_return": 0.12,
        "max_drawdown": 0.18,
        "volatility": 0.28,
        "dividends": 0.005,
        "splits": 0.0,
        "corporate_actions": [],
    },
    "ZOMATO": {
        "entry_price": 200.0,
        "current_price": 150.0,
        "total_return": -0.25,
        "benchmark_return": 0.10,
        "sector_return": -0.05,
        "max_drawdown": 0.35,
        "volatility": 0.45,
        "dividends": 0.0,
        "splits": 0.0,
        "corporate_actions": [{"type": "dilution", "note": "ESOP"}],
    },
}

_OVERRIDES: dict[str, dict[str, Any]] = {}


def reset_market() -> None:
    _OVERRIDES.clear()


def inject_outcome(ticker: str, outcome: dict[str, Any]) -> None:
    """Test/suite helper — versioned outcome override for a ticker."""
    _OVERRIDES[str(ticker or "").upper()] = deepcopy(outcome)


def collect_outcome(
    ticker: str | None,
    *,
    as_of: str | None = None,
    override: dict[str, Any] | None = None,
    scenario_realised: str | None = None,
) -> dict[str, Any]:
    symbol = str(ticker or "").upper()
    base = deepcopy(_OVERRIDES.get(symbol) or _SEED_PATHS.get(symbol) or {})
    if override:
        base.update(deepcopy(override))
    if not base:
        return {
            "found": False,
            "market_version": MARKET_VERSION,
            "ticker": symbol or None,
            "reason": "no_market_path",
        }

    total = float(base.get("total_return") or 0.0)
    bench = float(base.get("benchmark_return") or 0.0)
    sector = float(base.get("sector_return") or 0.0)
    alpha = round(total - bench, 6)
    as_of = as_of or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "found": True,
        "market_version": MARKET_VERSION,
        "ticker": symbol,
        "as_of": as_of,
        "versioned": True,
        "current_price": base.get("current_price"),
        "entry_price": base.get("entry_price"),
        "total_return": total,
        "benchmark_return": bench,
        "sector_return": sector,
        "alpha": alpha,
        "maximum_drawdown": float(base.get("max_drawdown") or base.get("maximum_drawdown") or 0.0),
        "volatility": float(base.get("volatility") or 0.0),
        "dividends": float(base.get("dividends") or 0.0),
        "splits": float(base.get("splits") or 0.0),
        "corporate_actions": list(base.get("corporate_actions") or []),
        "scenario_realised": scenario_realised or base.get("scenario_realised"),
    }
