"""Universe coverage registry — Universe Tiers for institutional depth.

Tier discipline: every company within a tier reaches Infosys-class depth
before the next tier expands. Soft registry only — does not invent live quotes.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.fundamentals.market_series import monthly_returns
from institutional_reasoning.fundamentals.primitives import covered_entities, has_primitives

UNIVERSE_VERSION = "universe-coverage-v1.1.0"

# Starter Nifty-50 subset — expand toward 100/500/global without claiming coverage.
NIFTY_50: tuple[str, ...] = (
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "BHARTIARTL",
    "SBIN", "HINDUNILVR", "LT", "BAJFINANCE", "HCLTECH", "AXISBANK", "MARUTI",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "NTPC", "POWERGRID", "ASIANPAINT",
    "WIPRO", "NESTLEIND", "M&M", "TATASTEEL", "ADANIENT", "JSWSTEEL", "ONGC",
    "COALINDIA", "TECHM", "BAJAJFINSV", "ADANIPORTS", "TATAMOTORS", "INDUSINDBK",
    "CIPLA", "GRASIM", "BPCL", "HINDALCO", "DRREDDY", "EICHERMOT", "APOLLOHOSP",
    "SBILIFE", "HDFCLIFE", "DIVISLAB", "BRITANNIA", "HEROMOTOCO", "TATACONSUM",
    "BAJAJ-AUTO", "SHRIRAMFIN", "TRENT", "BEL",
)

NIFTY_100_EXTRA: tuple[str, ...] = (
    "ZOMATO", "PERSISTENT", "DMART", "PIDILITIND", "HAVELLS", "SIEMENS",
    "DLF", "GODREJCP", "AMBUJACEM", "ICICIPRULI", "NAUKRI", "INDIGO",
    "ABB", "ADANIGREEN", "ALKEM", "AUROPHARMA", "BANKBARODA", "BOSCHLTD",
    "CANBK", "CHOLAFIN", "COLPAL", "DABUR", "HAL", "ICICIGI",
    "INDHOTEL", "IOC", "IRCTC", "JINDALSTEL", "LTIM", "LUPIN",
    "MARICO", "MAXHEALTH", "MUTHOOTFIN", "NHPC", "NMDC", "OFSS",
    "PAGEIND", "PETRONET", "PFC", "POLYCAB", "RECLTD", "SAIL",
    "SBICARD", "SHREECEM", "SRF", "TVSMOTOR", "VBL", "YESBANK",
    "ZYDUSLIFE", "BERGEPAINT",
)

GLOBAL_SEED: tuple[str, ...] = (
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK.B", "JPM", "V", "UNH",
)

# Universe Tiers — quality before breadth.
# Tier 1: Nifty 100 — institutional depth (complete)
# Tier 2: Remaining Nifty 500 — same institutional depth (Track 1)
# Tier 3: Mid-cap / thematic watchlists — expand as needed
# Tier 4: Global large-cap — S&P 500, Nasdaq-100, FTSE 100, Euro Stoxx 50, Nikkei 225
TIERS = ("tier_1_nifty_100", "tier_2_nifty_500", "tier_3_midcap_thematic", "tier_4_global")


def _nifty_500() -> tuple[str, ...]:
    try:
        from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500

        return tuple(NIFTY_500)
    except Exception:
        return tuple(dict.fromkeys([*NIFTY_50, *NIFTY_100_EXTRA]))


def _status(ticker: str) -> dict[str, Any]:
    t = ticker.upper()
    prim = has_primitives(t)
    risk = monthly_returns(t) is not None
    if prim and risk:
        level = "full"
    elif prim:
        level = "fundamentals"
    elif risk:
        level = "risk_only"
    else:
        level = "uncovered"
    return {
        "ticker": t,
        "primitives": prim,
        "risk_series": risk,
        "coverage": level,
    }


def coverage_for(ticker: str) -> dict[str, Any]:
    return {
        "universe_version": UNIVERSE_VERSION,
        **_status(ticker),
    }


def tier_report(tier: str = "nifty_50") -> dict[str, Any]:
    tier = tier.lower()
    if tier in {"nifty_50", "tier_0_nifty_50"}:
        symbols = NIFTY_50
        tier_label = "nifty_50"
    elif tier in {"nifty_100", "tier_1", "tier_1_nifty_100"}:
        symbols = tuple(dict.fromkeys([*NIFTY_50, *NIFTY_100_EXTRA]))
        tier_label = "tier_1_nifty_100"
    elif tier in {"nifty_500", "tier_2", "tier_2_nifty_500"}:
        symbols = _nifty_500()
        tier_label = "tier_2_nifty_500"
    elif tier in {"midcap", "thematic", "tier_3", "tier_3_midcap_thematic"}:
        symbols = ()
        tier_label = "tier_3_midcap_thematic"
    elif tier in {"global", "tier_4", "tier_4_global"}:
        symbols = GLOBAL_SEED
        tier_label = "tier_4_global"
    else:
        symbols = NIFTY_50
        tier_label = tier

    rows = [_status(s) for s in symbols] if symbols else []
    by_level = {"full": 0, "fundamentals": 0, "risk_only": 0, "uncovered": 0}
    for r in rows:
        by_level[r["coverage"]] = by_level.get(r["coverage"], 0) + 1
    covered_n = by_level["full"] + by_level["fundamentals"] + by_level["risk_only"]
    declared = len(symbols)
    return {
        "universe_version": UNIVERSE_VERSION,
        "tier": tier_label,
        "declared": declared,
        "covered": covered_n,
        "coverage_pct": round(100.0 * covered_n / declared, 2) if declared else 0.0,
        "by_level": by_level,
        "primitive_entities": covered_entities(),
        "rows": rows,
        "honest_gap": {
            "tier_3_midcap_thematic": tier_label == "tier_3_midcap_thematic",
            "tier_4_global_live_quotes": tier_label == "tier_4_global",
            "note": (
                "Uncovered symbols are reported explicitly — never silently filled. "
                "Tier quality gate: institutional depth before next tier expands."
            ),
        },
    }


def universe_tiers() -> dict[str, Any]:
    """Universe Tier board — quality standard before breadth."""
    t1 = tier_report("tier_1_nifty_100")
    t2 = tier_report("tier_2_nifty_500")
    t3 = tier_report("tier_3_midcap_thematic")
    t4 = tier_report("tier_4_global")
    return {
        "universe_version": UNIVERSE_VERSION,
        "discipline": "tier_quality_before_breadth",
        "north_star": "institutional_decision_coverage",
        "target": "500/500 Infosys-class depth on Tier 2 before Tier 3/4",
        "tiers": {
            "tier_1_nifty_100": {
                **{k: t1[k] for k in ("declared", "covered", "coverage_pct", "by_level")},
                "standard": "institutional_depth",
                "status": "complete" if t1["by_level"].get("full") == t1["declared"] else "in_progress",
            },
            "tier_2_nifty_500": {
                **{k: t2[k] for k in ("declared", "covered", "coverage_pct", "by_level")},
                "standard": "institutional_depth",
                "status": "complete" if t2["by_level"].get("full") == 500 else "in_progress",
            },
            "tier_3_midcap_thematic": {
                **{k: t3[k] for k in ("declared", "covered", "coverage_pct", "by_level")},
                "standard": "institutional_depth",
                "status": "deferred",
                "note": "Expand only after Tier 2 exit gate.",
            },
            "tier_4_global": {
                **{k: t4[k] for k in ("declared", "covered", "coverage_pct", "by_level")},
                "standard": "institutional_depth",
                "universes": ["SPX", "NDX", "UKX", "SX5E", "NKY"],
                "status": "deferred",
                "note": "S&P 500 / Nasdaq-100 / FTSE 100 / Euro Stoxx 50 / Nikkei 225 — after Tier 2/3.",
            },
        },
    }


def universe_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "universe_version": UNIVERSE_VERSION,
        "tiers": {
            t: tier_report(t)
            for t in ("nifty_50", "nifty_100", "nifty_500", "global")
        },
        "universe_tiers": universe_tiers(),
    }
