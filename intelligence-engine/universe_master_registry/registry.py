"""Build Universe Master Registry rows from real, uploaded universe files.

Source of truth (never hardcoded):
  * trading_universe  — full NSE cash equity book (EQUITY_L → NIFTYstocks.csv)
  * market_indices    — Nifty 50/Next50/100/200/500/Midcap Select/Bank/Fin Services

Institutional coverage / knowledge fields are soft-joined from ICF and IKT
when reachable. If unavailable, they stay None — never fabricated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

UNIVERSE_MASTER_VERSION = "universe-master-registry-v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _market_cap_category(market_cap: float | None) -> str | None:
    """Categorize only when a real market cap value exists (never guessed)."""
    if market_cap is None:
        return None
    try:
        cr = float(market_cap)  # expressed in INR crore, when supplied
    except (TypeError, ValueError):
        return None
    if cr >= 100_000:
        return "Large Cap"
    if cr >= 20_000:
        return "Mid Cap"
    return "Small Cap"


def _index_membership(symbol: str) -> list[str]:
    try:
        from market_indices.loader import membership_for_symbol

        return list(membership_for_symbol(symbol).get("indices") or [])
    except Exception:
        return []


def _icf_signals(symbol: str) -> dict[str, Any]:
    """Soft join — institutional coverage / knowledge confidence. Never fabricate:
    on any failure, every field stays None with an explicit "unavailable" note.
    """
    try:
        from institutional_coverage_factory.production import icc_status_for

        icc = icc_status_for(symbol) or {}
        if not icc.get("ok"):
            raise RuntimeError(icc.get("error") or "icc_unavailable")
        return {
            "institutional_coverage": bool(icc.get("institutional_coverage_complete")),
            "coverage_state": icc.get("status"),
            "coverage_pct": icc.get("coverage_pct"),
            "knowledge_confidence": icc.get("knowledge_confidence"),
            "research_ready": icc.get("research_readiness_score") is not None
            and float(icc.get("research_readiness_score") or 0) >= 0.8,
            "claim_safe": icc.get("claim_safe"),
            "missing_classes": icc.get("missing_classes"),
            "signal_source": "institutional_coverage_factory",
        }
    except Exception as exc:
        return {
            "institutional_coverage": None,
            "coverage_state": "unavailable",
            "coverage_pct": None,
            "knowledge_confidence": None,
            "research_ready": None,
            "claim_safe": None,
            "missing_classes": None,
            "signal_source": None,
            "signal_error": str(exc)[:160],
        }


def _ikt_company_name(symbol: str) -> tuple[str | None, str | None]:
    """Company name / market cap from IKT company_master + valuation, if recorded."""
    try:
        from institutional_knowledge_tables.store import get_table

        master = get_table(symbol, "company_master")
        row = master.get("row") if isinstance(master, dict) else {}
        name_cell = (row or {}).get("company_name")
        name = name_cell.get("value") if isinstance(name_cell, dict) else None
        valuation = get_table(symbol, "valuation")
        vrow = valuation.get("row") if isinstance(valuation, dict) else {}
        _ = vrow
        return name, None
    except Exception:
        return None, None


def build_company_row(symbol: str, *, include_coverage: bool = False) -> dict[str, Any] | None:
    from trading_universe.loader import get_symbol

    base = get_symbol(symbol)
    if not base:
        return None
    ticker = base["symbol"]
    ikt_name, market_cap = _ikt_company_name(ticker)
    row: dict[str, Any] = {
        "company_name": ikt_name or base.get("name"),
        "ticker": ticker,
        "isin": base.get("isin") or None,
        "exchange": "NSE",
        "sector": None,
        "industry": base.get("industry") or None,
        "market_cap_category": _market_cap_category(market_cap),
        "index_membership": _index_membership(ticker),
        "status": "active" if base.get("tradable") else "inactive",
        "series": base.get("series"),
        "last_updated": _now(),
        "source": "trading_universe+market_indices",
    }
    if include_coverage:
        row.update(_icf_signals(ticker))
    else:
        row.update(
            {
                "institutional_coverage": None,
                "coverage_state": None,
                "knowledge_confidence": None,
                "research_ready": None,
                "claim_safe": None,
                "signal_source": None,
            }
        )
    return row


def get_company(ticker: str) -> dict[str, Any]:
    row = build_company_row(ticker, include_coverage=True)
    if not row:
        return {
            "ok": False,
            "ticker": str(ticker or "").upper(),
            "error": "not_in_universe_master_registry",
            "hint": "Ticker is not in the uploaded EQUITY_L / NIFTYstocks trading book.",
        }
    return {"ok": True, "version": UNIVERSE_MASTER_VERSION, **row}


def list_registry(
    *,
    index: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    include_coverage: bool = False,
) -> dict[str, Any]:
    from trading_universe.loader import list_symbols

    symbols = list_symbols()
    if index:
        try:
            from market_indices.loader import list_members

            idx_syms = {m["symbol"] for m in list_members(index)}
            symbols = [s for s in symbols if s in idx_syms]
        except Exception:
            symbols = []
    total = len(symbols)
    page = symbols[offset : offset + limit] if limit is not None else symbols[offset:]
    rows = [build_company_row(s, include_coverage=include_coverage) for s in page]
    rows = [r for r in rows if r]
    return {
        "ok": True,
        "version": UNIVERSE_MASTER_VERSION,
        "total": total,
        "count": len(rows),
        "offset": offset,
        "limit": limit,
        "index_filter": index,
        "rows": rows,
    }


def dashboard() -> dict[str, Any]:
    from knowledge_factory.historical_depth.universe_priority import universe_summary
    from trading_universe.loader import equity_l_path, health as tu_health

    tu = tu_health()
    summary = universe_summary()
    return {
        "ok": True,
        "version": UNIVERSE_MASTER_VERSION,
        "generated_at": _now(),
        "source_files": {
            "trading_universe_path": tu.get("path"),
            "equity_l_path": str(equity_l_path()) if equity_l_path() else None,
        },
        "trading_universe_count": tu.get("count"),
        "index_summary": summary,
        "mission": (
            "Single master registry sourced from the uploaded equity universe file. "
            "New listings in the file are onboarded automatically — no hardcoded tickers."
        ),
    }
