"""Supported listed-company universe with smart backfill prioritisation.

Priority (lower = sooner):
  1 Nifty 50
  2 Nifty Next 50
  3 Nifty 100 residual
  4 Nifty 200 residual
  5 Nifty 500 residual
  6 Bank / Financial Services thematic (if not already higher)
  7 Full NSE trading book (EQUITY_L / NIFTYstocks)
"""

from __future__ import annotations

from typing import Any


def _tickers_from_rows(rows: list[dict[str, Any]] | list[Any]) -> list[str]:
    out: list[str] = []
    for r in rows:
        if isinstance(r, dict):
            t = str(r.get("ticker") or r.get("symbol") or "").upper()
        else:
            t = str(r or "").upper()
        if t:
            out.append(t)
    return out


def _index_symbols(index_id: str) -> list[str]:
    try:
        from market_indices.loader import list_members

        return [m["symbol"] for m in list_members(index_id) if m.get("symbol")]
    except Exception:
        return []


def nifty_50() -> list[str]:
    syms = _index_symbols("NIFTY_50")
    if syms:
        return syms
    try:
        from institutional_reasoning.fundamentals.universe import NIFTY_50

        return list(NIFTY_50)
    except Exception:
        try:
            from app.kc.universes import nifty50_tickers

            return sorted(nifty50_tickers())
        except Exception:
            return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY"]


def nifty_next_50() -> list[str]:
    syms = _index_symbols("NIFTY_NEXT_50")
    if syms:
        return syms
    try:
        from app.kc.universes import nifty_next50_tickers

        return sorted(nifty_next50_tickers())
    except Exception:
        try:
            from institutional_reasoning.fundamentals.universe import NIFTY_100_EXTRA

            return list(NIFTY_100_EXTRA)[:50]
        except Exception:
            return []


def nifty_100() -> list[str]:
    syms = _index_symbols("NIFTY_100")
    if syms:
        return syms
    try:
        from knowledge_factory.coverage import NIFTY_100

        return list(NIFTY_100)
    except Exception:
        return list(dict.fromkeys([*nifty_50(), *nifty_next_50()]))


def nifty_200() -> list[str]:
    syms = _index_symbols("NIFTY_200")
    if syms:
        return syms
    return list(nifty_100())


def nifty_500() -> list[str]:
    syms = _index_symbols("NIFTY_500")
    if syms:
        return syms
    try:
        from knowledge_factory.coverage import NIFTY_500

        return list(NIFTY_500)
    except Exception:
        try:
            from institutional_reasoning.fundamentals.nifty500_universe import NIFTY_500 as N5

            return list(N5)
        except Exception:
            return list(dict.fromkeys([*nifty_50(), *nifty_next_50()]))


def nifty_bank() -> list[str]:
    return _index_symbols("NIFTY_BANK")


def nifty_financial_services() -> list[str]:
    return _index_symbols("NIFTY_FINANCIAL_SERVICES")


def nifty_midcap_select() -> list[str]:
    return _index_symbols("NIFTY_MIDCAP_SELECT")


def nse_listed() -> list[str]:
    """Full NSE cash equities available for trading (EQUITY_L → NIFTYstocks)."""
    try:
        from trading_universe.loader import list_symbols

        return list_symbols()
    except Exception:
        return []


def supported_universe() -> list[str]:
    """Full supported listed set: index books ∪ NSE EQUITY_L trading book."""
    return list(
        dict.fromkeys(
            [
                *nifty_50(),
                *nifty_next_50(),
                *nifty_100(),
                *nifty_200(),
                *nifty_500(),
                *nifty_midcap_select(),
                *nifty_bank(),
                *nifty_financial_services(),
                *nse_listed(),
            ]
        )
    )


def priority_tier(symbol: str) -> int:
    """Lower number = higher priority."""
    s = symbol.upper()
    if s in set(nifty_50()):
        return 1
    if s in set(nifty_next_50()):
        return 2
    if s in set(nifty_100()):
        return 3
    if s in set(nifty_200()):
        return 4
    if s in set(nifty_500()) or s in set(nifty_midcap_select()):
        return 5
    if s in set(nifty_bank()) or s in set(nifty_financial_services()):
        return 6
    if s in set(nse_listed()):
        return 7
    return 8


def prioritised_universe(*, coverage_years: dict[str, float] | None = None) -> list[str]:
    """Index tiers first, then residual NSE; within tier lowest coverage first."""
    coverage_years = coverage_years or {}
    universe = supported_universe()
    return sorted(
        universe,
        key=lambda s: (
            priority_tier(s),
            float(coverage_years.get(s.upper(), 0.0)),
            s,
        ),
    )


def tier_label(tier: int) -> str:
    return {
        1: "nifty_50",
        2: "nifty_next_50",
        3: "nifty_100",
        4: "nifty_200",
        5: "nifty_500",
        6: "nifty_thematic",
        7: "nse_listed",
        8: "other",
    }.get(tier, "other")


def universe_summary() -> dict[str, Any]:
    return {
        "nifty_50": len(nifty_50()),
        "nifty_next_50": len(nifty_next_50()),
        "nifty_100": len(nifty_100()),
        "nifty_200": len(nifty_200()),
        "nifty_500": len(nifty_500()),
        "nifty_midcap_select": len(nifty_midcap_select()),
        "nifty_bank": len(nifty_bank()),
        "nifty_financial_services": len(nifty_financial_services()),
        "nse_listed": len(nse_listed()),
        "supported_unique": len(supported_universe()),
    }
