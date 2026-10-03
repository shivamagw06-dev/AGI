"""What each desk and strategy is allowed to read.

Ranks stay on the feed they were designed for. Display fields that must track
the tape overlay from live_market_snapshots. Trailing PE/PB stay on the latest
Upstox warehouse print — they are not recomputed from LTP.
"""

from __future__ import annotations

from typing import Any

LIVE_LTP = "live_market_snapshots + Live Alpha tape"
LATEST_PE = "warehouse.valuation_ratios (Upstox EOD)"
EOD_CLOSE = "warehouse.daily_market_history"
EOD_FUNDAMENTALS = "warehouse.historical_ratios"
CONSENSUS = "warehouse.consensus"
LIVE_SIGNALS = "live_alpha_signals (session-fresh)"
LIVE_INDEX = "Groww/Yahoo index snapshot (home strip)"
GROWW_DAILY = "Groww/Upstox daily candles"
ATR_ADV = "vendor_risk_metrics + vendor_liquidity (EOD)"

# Pages: display contract. `price` is what the user sees as the current quote.
PAGES: dict[str, dict[str, Any]] = {
    "/": {"price": LIVE_INDEX, "body": "editorial CMS", "notes": "Header strip only."},
    "/hedge-fund": {
        "price": LIVE_LTP,
        "valuation": LATEST_PE,
        "signals": LIVE_SIGNALS,
        "fundamentals": EOD_FUNDAMENTALS,
    },
    "/hedge-fund/alpha-opportunities": {
        "price": LIVE_LTP,
        "valuation": LATEST_PE,
        "signals": LIVE_SIGNALS,
        "eod_confirm": GROWW_DAILY,
    },
    "/live-alpha": {
        "price": LIVE_LTP,
        "signals": LIVE_SIGNALS,
        "sector_rotation": GROWW_DAILY,
        "equity_screen": GROWW_DAILY,
    },
    "/live-desk": {"price": LIVE_INDEX, "signals": LIVE_SIGNALS},
    "/valuation-terminal": {"price": EOD_CLOSE, "valuation": LATEST_PE, "notes": "PE must stay on EOD earnings."},
    "/valuation-intelligence": {"price": "consensus book CMP", "valuation": CONSENSUS},
    "/market-sector-intelligence": {"price": LIVE_INDEX, "valuation": LATEST_PE},
    "/markets": {"price": "Trendlyne/TradingView widgets"},
    "/economics": {"price": "Yahoo/Upstox FX (delayed live)"},
    "/sectors/:id": {"valuation": "UI sector snapshot, not LTP"},
    "/themes/:id": {"body": "research snapshot"},
    "/predictions": {"body": "research tracker, not LTP"},
    "/workspace": {"body": "local only"},
    "/ask": {"body": "research desk, not a quote feed"},
}

# Strategies: rank vs display. Rank never uses LTP unless the engine is intraday.
STRATEGIES: dict[str, dict[str, Any]] = {
    "value": {"rank": LATEST_PE, "display_price": LIVE_LTP, "surface": "HFL"},
    "quality": {"rank": EOD_FUNDAMENTALS, "display_price": LIVE_LTP, "surface": "HFL"},
    "conviction": {"rank": CONSENSUS, "display_price": LIVE_LTP, "derived": "target/LTP upside", "surface": "HFL"},
    "pairs": {"rank": LATEST_PE, "display_price": LIVE_LTP, "surface": "HFL"},
    "stress": {"rank": f"{EOD_FUNDAMENTALS} + 1y {EOD_CLOSE}", "display_price": LIVE_LTP, "surface": "HFL"},
    "alpha": {"rank": "warehouse.hedge_fund_factors", "display_price": LIVE_LTP, "surface": "HFL"},
    "growth": {"rank": f"trailing {LATEST_PE} / forward PE", "display_price": LIVE_LTP, "surface": "HFL"},
    "dividend": {"rank": "warehouse yield + quality gates", "display_price": LIVE_LTP, "derived": "DPS/LTP yield", "surface": "HFL"},
    "live_alpha": {"rank": LIVE_SIGNALS, "display_price": LIVE_LTP, "surface": "HFL"},
    "opening_range_breakout": {"rank": LIVE_SIGNALS, "display_price": LIVE_LTP, "size": ATR_ADV, "surface": "HFL live"},
    "intraday_reversion": {"rank": LIVE_SIGNALS, "display_price": LIVE_LTP, "size": ATR_ADV, "surface": "HFL live"},
    "flow_anomaly": {"rank": LIVE_SIGNALS, "display_price": LIVE_LTP, "size": ATR_ADV, "surface": "HFL live"},
    "cross_sectional_momentum_v1": {"rank": "live 15m/60m residual vs sector", "display_price": LIVE_LTP, "surface": "Live Alpha"},
    "volume_liquidity_anomaly_v1": {"rank": "live volume z vs TOD baseline", "display_price": LIVE_LTP, "surface": "Live Alpha"},
    "opening_range_expansion_v1": {"rank": "live LTP vs opening range", "display_price": LIVE_LTP, "surface": "Live Alpha"},
    "intraday_mean_reversion_v1": {"rank": "live residual shock", "display_price": LIVE_LTP, "surface": "Live Alpha"},
    "derivatives_positioning_v1": {"rank": "live futures LTP + OI", "display_price": LIVE_LTP, "surface": "Live Alpha"},
    "agi_sector_rotation_v1": {"rank": GROWW_DAILY, "display_price": GROWW_DAILY, "surface": "Live Alpha EOD"},
    "agi_equity_opportunity_v1": {"rank": GROWW_DAILY, "display_price": LIVE_LTP, "surface": "Live Alpha EOD"},
}

NEEDS_LIVE_PRICE = frozenset(
    key for key, spec in STRATEGIES.items() if spec.get("display_price") == LIVE_LTP
)
NEEDS_LIVE_SIGNALS = frozenset(
    key for key, spec in STRATEGIES.items() if spec.get("rank") == LIVE_SIGNALS or "live 15m" in str(spec.get("rank"))
)
NEEDS_LATEST_PE = frozenset(
    key for key, spec in STRATEGIES.items() if LATEST_PE in str(spec.get("rank"))
)


def contract_for(strategy_id: str) -> dict[str, Any]:
    return dict(STRATEGIES.get(str(strategy_id or "").strip(), {}))
