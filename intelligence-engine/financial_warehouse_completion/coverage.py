"""Universe financial coverage — packs, gaps, sector/industry rollups."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from financial_warehouse_completion.models import (
    ENGINE_CODE,
    MIN_ANNUAL_YEARS,
    MIN_QUARTERLY_PERIODS,
    PREFERRED_ANNUAL_YEARS,
    PROGRAMME_CODE,
    PROGRAMME_VERSION,
    TARGETS,
)
from financial_warehouse_completion.share_count import has_share_count


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(numer: int, denom: int) -> float:
    if denom <= 0:
        return 0.0
    return round(100.0 * numer / denom, 1)


def _entity_count(tab: str, symbol: str) -> int:
    from institutional_warehouse import store

    try:
        return int(store.fetch(tab, entity=symbol, limit=1).get("total") or 0)
    except Exception:
        try:
            return len(store.all_rows(tab, entity=symbol, limit=500) or [])
        except Exception:
            return 0


def _statement_depth(tab: str, symbol: str, period_key: str) -> int:
    """Count distinct fiscal periods, not duplicate source/statement rows."""
    from institutional_warehouse import store

    try:
        rows = store.all_rows(tab, entity=symbol, limit=500) or []
    except Exception:
        rows = []
    return len({str(row.get(period_key) or "").strip().upper() for row in rows if row.get(period_key)})


def company_coverage(symbol: str) -> dict[str, Any]:
    """Per-company pack coverage used by HVIE / RIE / FIE consumers."""
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    master = None
    try:
        rows = store.fetch("company_master", filters={"symbol": ticker}, limit=1).get("rows") or []
        master = rows[0] if rows else None
    except Exception:
        master = None

    annual_n = _entity_count("financials_annual", ticker)
    quarterly_n = _entity_count("financials_quarterly", ticker)
    annual_periods = _statement_depth("financials_annual", ticker, "fiscal_year")
    quarterly_periods = _statement_depth("financials_quarterly", ticker, "fiscal_period")
    share_ok, shares = has_share_count(ticker)
    consensus_n = _entity_count("consensus", ticker)
    ownership_n = _entity_count("ownership", ticker)
    peers_n = _entity_count("peer_relationships", ticker)
    profile_n = _entity_count("profile_history", ticker)
    share_hist_n = _entity_count("share_count_history", ticker)

    packs = {
        "company_master": bool(master),
        "financials_annual": annual_periods >= MIN_ANNUAL_YEARS,
        "financials_quarterly": quarterly_periods >= MIN_QUARTERLY_PERIODS,
        "share_count_history": share_ok,
        "consensus": consensus_n >= 1,
        "ownership": ownership_n >= 1,
        "peer_relationships": peers_n >= 1,
        "profile_history": profile_n >= 1,
    }
    financial_ok = packs["financials_annual"] or packs["financials_quarterly"]
    preferred = {
        "annual_10y": annual_periods >= PREFERRED_ANNUAL_YEARS,
        "quarterly_8q": quarterly_periods >= 8,
    }
    missing = [k for k, v in packs.items() if not v]
    return {
        "ok": True,
        "symbol": ticker,
        "company_name": (master or {}).get("company_name"),
        "isin": (master or {}).get("isin"),
        "sector": (master or {}).get("sector"),
        "industry": (master or {}).get("industry"),
        "counts": {
            "annual": annual_n,
            "quarterly": quarterly_n,
            "annual_periods": annual_periods,
            "quarterly_periods": quarterly_periods,
            "share_count_history": share_hist_n,
            "consensus": consensus_n,
            "ownership": ownership_n,
            "peers": peers_n,
            "profiles": profile_n,
        },
        "packs": packs,
        "financial_ok": financial_ok,
        "preferred": preferred,
        "strategy_ready": bool(financial_ok and preferred["quarterly_8q"]),
        "share_count_ok": share_ok,
        "shares_outstanding": shares,
        "missing_packs": missing,
        "hvie_ready": financial_ok and share_ok,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def missing_statements(*, limit: int = 500) -> dict[str, Any]:
    from institutional_warehouse import store

    masters = store.all_rows("company_master", limit=100000) or []
    missing_annual: list[dict[str, Any]] = []
    missing_quarterly: list[dict[str, Any]] = []
    for m in masters:
        sym = str(m.get("symbol") or "").upper()
        if not sym:
            continue
        a = _entity_count("financials_annual", sym)
        q = _entity_count("financials_quarterly", sym)
        if a < MIN_ANNUAL_YEARS:
            missing_annual.append({
                "symbol": sym,
                "company_name": m.get("company_name"),
                "sector": m.get("sector"),
                "annual_rows": a,
                "need": MIN_ANNUAL_YEARS,
            })
        if q < MIN_QUARTERLY_PERIODS:
            missing_quarterly.append({
                "symbol": sym,
                "company_name": m.get("company_name"),
                "sector": m.get("sector"),
                "quarterly_rows": q,
                "need": MIN_QUARTERLY_PERIODS,
            })
    return {
        "ok": True,
        "missing_annual": missing_annual[: max(1, min(int(limit), 5000))],
        "missing_quarterly": missing_quarterly[: max(1, min(int(limit), 5000))],
        "counts": {
            "missing_annual": len(missing_annual),
            "missing_quarterly": len(missing_quarterly),
            "universe": len(masters),
        },
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def missing_share_count(*, limit: int = 500) -> dict[str, Any]:
    from institutional_warehouse import store

    masters = store.all_rows("company_master", limit=100000) or []
    missing: list[dict[str, Any]] = []
    for m in masters:
        sym = str(m.get("symbol") or "").upper()
        if not sym:
            continue
        ok, _ = has_share_count(sym)
        if not ok:
            missing.append({
                "symbol": sym,
                "company_name": m.get("company_name"),
                "sector": m.get("sector"),
                "isin": m.get("isin"),
            })
    return {
        "ok": True,
        "rows": missing[: max(1, min(int(limit), 5000))],
        "count": len(missing),
        "universe": len(masters),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def financial_coverage() -> dict[str, Any]:
    """Board-level coverage for /admin/financial-warehouse."""
    from institutional_warehouse import store

    masters = store.all_rows("company_master", limit=100000) or []
    universe = len(masters)
    annual_ok = quarterly_ok = share_ok = consensus_ok = ownership_ok = 0
    peers_ok = profile_ok = financial_ok = hvie_ready = 0
    by_sector: dict[str, dict[str, int]] = defaultdict(
        lambda: {"companies": 0, "annual": 0, "quarterly": 0, "share_count": 0, "hvie_ready": 0}
    )
    by_industry: dict[str, dict[str, int]] = defaultdict(
        lambda: {"companies": 0, "annual": 0, "quarterly": 0, "share_count": 0}
    )

    for m in masters:
        sym = str(m.get("symbol") or "").upper()
        if not sym:
            continue
        sector = str(m.get("sector") or "Unknown")
        industry = str(m.get("industry") or m.get("industry_dna") or "Unknown")
        by_sector[sector]["companies"] += 1
        by_industry[industry]["companies"] += 1

        a = _entity_count("financials_annual", sym) >= MIN_ANNUAL_YEARS
        q = _entity_count("financials_quarterly", sym) >= MIN_QUARTERLY_PERIODS
        s_ok, _ = has_share_count(sym)
        c = _entity_count("consensus", sym) >= 1
        o = _entity_count("ownership", sym) >= 1
        p = _entity_count("peer_relationships", sym) >= 1
        pr = _entity_count("profile_history", sym) >= 1
        fin = a or q
        ready = fin and s_ok

        annual_ok += int(a)
        quarterly_ok += int(q)
        share_ok += int(s_ok)
        consensus_ok += int(c)
        ownership_ok += int(o)
        peers_ok += int(p)
        profile_ok += int(pr)
        financial_ok += int(fin)
        hvie_ready += int(ready)
        if a:
            by_sector[sector]["annual"] += 1
            by_industry[industry]["annual"] += 1
        if q:
            by_sector[sector]["quarterly"] += 1
            by_industry[industry]["quarterly"] += 1
        if s_ok:
            by_sector[sector]["share_count"] += 1
            by_industry[industry]["share_count"] += 1
        if ready:
            by_sector[sector]["hvie_ready"] += 1

    # HVIE completion from universe queue when present
    hvie_complete = 0
    hvie_universe = universe
    try:
        from historical_valuation_intelligence.universe_programme.production import coverage as hvie_cov

        hc = hvie_cov() or {}
        hvie_complete = int((hc.get("pipeline") or {}).get("complete") or 0)
        hvie_universe = int(hc.get("universe") or universe) or universe
    except Exception:
        try:
            qrows = store.all_rows("hvie_universe_queue", limit=100000) or []
            hvie_complete = sum(
                1 for r in qrows if str(r.get("lifecycle") or "").upper() == "COMPLETE"
            )
            hvie_universe = len(qrows) or universe
        except Exception:
            pass

    metrics = {
        "annual_pct": _pct(annual_ok, universe),
        "quarterly_pct": _pct(quarterly_ok, universe),
        "share_count_pct": _pct(share_ok, universe),
        "company_financial_pct": _pct(financial_ok, universe),
        "consensus_pct": _pct(consensus_ok, universe),
        "ownership_pct": _pct(ownership_ok, universe),
        "peers_pct": _pct(peers_ok, universe),
        "profile_pct": _pct(profile_ok, universe),
        "hvie_eligible_pct": _pct(hvie_ready, universe),
        "hvie_complete_pct": _pct(hvie_complete, hvie_universe),
    }
    targets_met = {k: metrics[k] >= TARGETS[k] for k in TARGETS if k in metrics}

    sector_rows = []
    for sec, c in sorted(by_sector.items(), key=lambda kv: -kv[1]["companies"]):
        n = max(c["companies"], 1)
        sector_rows.append({
            "sector": sec,
            **c,
            "annual_pct": _pct(c["annual"], n),
            "quarterly_pct": _pct(c["quarterly"], n),
            "share_count_pct": _pct(c["share_count"], n),
            "hvie_ready_pct": _pct(c["hvie_ready"], n),
        })

    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "universe": universe,
        "counts": {
            "annual_ok": annual_ok,
            "quarterly_ok": quarterly_ok,
            "share_count_ok": share_ok,
            "financial_ok": financial_ok,
            "consensus_ok": consensus_ok,
            "ownership_ok": ownership_ok,
            "peers_ok": peers_ok,
            "profile_ok": profile_ok,
            "hvie_ready": hvie_ready,
            "hvie_complete": hvie_complete,
        },
        "metrics": metrics,
        "targets": TARGETS,
        "targets_met": targets_met,
        "plain_english": (
            f"{financial_ok} of {universe} companies have usable statements "
            f"({metrics['company_financial_pct']}%). "
            f"Share counts: {metrics['share_count_pct']}%. "
            f"HVIE-ready: {metrics['hvie_eligible_pct']}%; HVIE complete: {metrics['hvie_complete_pct']}%."
        ),
        "by_sector": sector_rows[:40],
        "rule": "never_import_vendor_historical_multiples",
        "checked_at": _now(),
    }
