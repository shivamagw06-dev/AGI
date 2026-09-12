"""Universe helpers — priority tiers TOP20 → NIFTY50 → NIFTY100 → UNIVERSE."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from institutional_coverage_factory.schema import PriorityTier


def top20_tickers() -> List[str]:
    from institutional_evidence.schema import PHASE1_TOP20

    return [str(r["ticker"]).upper() for r in PHASE1_TOP20]


def nifty50_tickers() -> List[str]:
    try:
        from market_indices.loader import list_members

        syms = [m["symbol"] for m in list_members("NIFTY_50") if m.get("symbol")]
        if syms:
            return syms
    except Exception:
        pass
    try:
        from institutional_reasoning.fundamentals.universe import NIFTY_50

        return [str(t).upper() for t in NIFTY_50]
    except Exception:
        return top20_tickers()


def nifty100_tickers() -> List[str]:
    try:
        from market_indices.loader import list_members

        syms = [m["symbol"] for m in list_members("NIFTY_100") if m.get("symbol")]
        if syms:
            return syms
    except Exception:
        pass
    try:
        from knowledge_factory.coverage import NIFTY_100

        return [str(t).upper() for t in NIFTY_100]
    except Exception:
        return nifty50_tickers()


def universe_tickers() -> List[str]:
    """Institutional coverage universe — prefer live Nifty 500 CSV, else full NSE book."""
    try:
        from market_indices.loader import list_members

        syms = [m["symbol"] for m in list_members("NIFTY_500") if m.get("symbol")]
        if syms:
            return syms
    except Exception:
        pass
    try:
        from trading_universe.loader import list_symbols

        all_eq = list_symbols()
        if all_eq:
            return all_eq
    except Exception:
        pass
    try:
        from knowledge_factory.coverage import NIFTY_500

        return [str(t).upper() for t in NIFTY_500]
    except Exception:
        return nifty100_tickers()


def tier_for_ticker(ticker: str) -> str:
    t = str(ticker or "").upper().strip()
    if t in set(top20_tickers()):
        return PriorityTier.TOP20.value
    if t in set(nifty50_tickers()):
        return PriorityTier.NIFTY50.value
    if t in set(nifty100_tickers()):
        return PriorityTier.NIFTY100.value
    return PriorityTier.UNIVERSE.value


def ordered_universe(priority: List[str] | Tuple[str, ...] | None = None) -> List[Dict[str, Any]]:
    """Return unique tickers in priority order with tier labels."""
    order = list(priority or [t.value for t in PriorityTier])
    buckets = {
        PriorityTier.TOP20.value: top20_tickers(),
        PriorityTier.NIFTY50.value: nifty50_tickers(),
        PriorityTier.NIFTY100.value: nifty100_tickers(),
        PriorityTier.UNIVERSE.value: universe_tickers(),
    }
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for tier in order:
        for t in buckets.get(tier, []):
            if t in seen:
                continue
            seen.add(t)
            out.append({"ticker": t, "priority_tier": tier_for_ticker(t)})
    return out
