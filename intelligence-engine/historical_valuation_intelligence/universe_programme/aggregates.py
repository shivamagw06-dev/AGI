"""Persist sector / industry / market historical medians (never calculate in UI)."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE, VERSION
from historical_valuation_intelligence.universe_programme.models import PROGRAMME_CODE


def _paged_rows(tab_id: str, *, max_rows: int = 200_000) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    page_size = 5000
    offset = 0
    out: list[dict[str, Any]] = []
    while offset < max_rows:
        try:
            page = store.fetch(tab_id, limit=page_size, offset=offset)
        except Exception:
            break
        rows = page.get("rows") or []
        if not rows:
            break
        out.extend(rows)
        total = int(page.get("total") or 0)
        offset += len(rows)
        if offset >= total or len(rows) < page_size:
            break
    return out


def _num(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        f = float(v)
        if f != f or f <= 0:
            return None
        return f
    except Exception:
        return None


def persist_cross_section_medians(
    *,
    as_of: Optional[str] = None,
    metric: str = "pe",
) -> dict[str, Any]:
    """Write sector + industry + market medians for one as-of date (latest CMP cross-section)."""
    from institutional_warehouse import gateway

    observed = as_of or date.today().isoformat()
    masters = {
        str(r.get("symbol") or "").upper(): r
        for r in _paged_rows("company_master", max_rows=20_000)
        if r.get("symbol")
    }
    latest: dict[str, dict[str, Any]] = {}
    for row in _paged_rows("historical_valuation", max_rows=200_000):
        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue
        prev = latest.get(sym)
        if not prev or str(row.get("date") or "") > str(prev.get("date") or ""):
            latest[sym] = row

    by_sector: dict[str, list[float]] = defaultdict(list)
    by_industry: dict[str, list[float]] = defaultdict(list)
    market_vals: list[float] = []

    for sym, row in latest.items():
        val = _num(row.get(metric))
        if val is None:
            continue
        m = masters.get(sym) or {}
        sector = str(m.get("sector") or "").strip()
        industry = str(m.get("industry") or m.get("industry_dna") or "").strip()
        market_vals.append(val)
        if sector:
            by_sector[sector].append(val)
        if industry:
            by_industry[industry].append(val)

    sector_rows = [
        {
            "sector": sec,
            "metric": metric,
            "as_of": observed,
            "median_value": round(statistics.median(vals), 4),
            "company_count": len(vals),
        }
        for sec, vals in sorted(by_sector.items())
        if len(vals) >= 2
    ]
    industry_rows = [
        {
            "industry": ind,
            "metric": metric,
            "as_of": observed,
            "median_value": round(statistics.median(vals), 4),
            "company_count": len(vals),
        }
        for ind, vals in sorted(by_industry.items())
        if len(vals) >= 2
    ]
    market_rows = []
    if len(market_vals) >= 2:
        market_rows.append({
            "market": "ALL",
            "metric": metric,
            "as_of": observed,
            "median_value": round(statistics.median(market_vals), 4),
            "company_count": len(market_vals),
        })

    written = {}
    if sector_rows:
        written["sector"] = gateway.write(
            "historical_sector_medians", sector_rows,
            source=ENGINE_CODE, actor=PROGRAMME_CODE, reason="hvie_sector_medians",
        )
    if industry_rows:
        written["industry"] = gateway.write(
            "historical_industry_medians", industry_rows,
            source=ENGINE_CODE, actor=PROGRAMME_CODE, reason="hvie_industry_medians",
        )
    if market_rows:
        written["market"] = gateway.write(
            "historical_market_medians", market_rows,
            source=ENGINE_CODE, actor=PROGRAMME_CODE, reason="hvie_market_medians",
        )

    return {
        "ok": True,
        "as_of": observed,
        "metric": metric,
        "sector_rows": len(sector_rows),
        "industry_rows": len(industry_rows),
        "market_rows": len(market_rows),
        "written": written,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }
