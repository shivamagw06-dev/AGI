"""Market, sector and industry aggregation from the warehouse universe."""

from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any, Optional

from valuation_terminal.sector_lens import lens_for


# Sector history is heterogeneous: the imported CapIQ sector series is annual,
# while HVIE may be daily/monthly.  A single 252-session gate incorrectly hid
# an otherwise valid 8–10 year annual series.  Use source-aware evidence and
# present the resulting coverage/confidence rather than demanding full daily
# history from every source.
MIN_ANNUAL_HISTORY_OBS = 2
MIN_GENERIC_HISTORY_OBS = 24
MIN_DAILY_HISTORY_OBS = 252


def _median(values: list[Any]) -> Optional[float]:
    clean = [float(v) for v in values if v is not None]
    return round(median(clean), 2) if clean else None


def _group_median(rows: list[dict[str, Any]], key: str, field: str) -> Optional[float]:
    return _median([r.get(field) for r in rows if r.get(key)])


def market_overview(universe: dict[str, Any]) -> dict[str, Any]:
    rows = universe.get("rows") or []
    if not rows:
        return {"ok": False, "error": "empty_universe"}

    pe_series = [r["pe"] for r in rows if r.get("pe") is not None]
    pb_series = [r["pb"] for r in rows if r.get("pb") is not None]
    ev_series = [r["ev_ebitda"] for r in rows if r.get("ev_ebitda") is not None]
    div_series = [r["dividend_yield"] for r in rows if r.get("dividend_yield") is not None]

    # Sector roll-ups for extremes.
    sectors: dict[str, list[dict[str, Any]]] = {}
    industries: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("sector"):
            sectors.setdefault(str(row["sector"]), []).append(row)
        if row.get("industry"):
            industries.setdefault(str(row["industry"]), []).append(row)

    sector_pe = {
        s: _median([r["pe"] for r in members if r.get("pe") is not None])
        for s, members in sectors.items()
        if len(members) >= 5
    }
    sector_pe = {k: v for k, v in sector_pe.items() if v is not None}
    cheapest_sector = min(sector_pe, key=sector_pe.get) if sector_pe else None
    expensive_sector = max(sector_pe, key=sector_pe.get) if sector_pe else None

    industry_pe = {
        i: _median([r["pe"] for r in members if r.get("pe") is not None])
        for i, members in industries.items()
        if len(members) >= 3
    }
    industry_pe = {k: v for k, v in industry_pe.items() if v is not None}
    cheapest_industry = min(industry_pe, key=industry_pe.get) if industry_pe else None
    expensive_industry = max(industry_pe, key=industry_pe.get) if industry_pe else None

    def _finite_change(row: dict[str, Any], field: str) -> bool:
        v = row.get(field)
        try:
            f = float(v)
        except (TypeError, ValueError):
            return False
        return abs(f) <= 150.0  # matches universe / rotation cap

    pe_expansion = sorted(
        [r for r in rows if _finite_change(r, "pe_change_pct")],
        key=lambda r: -(r["pe_change_pct"] or 0),
    )[:5]
    pe_compression = sorted(
        [r for r in rows if _finite_change(r, "pe_change_pct")],
        key=lambda r: r["pe_change_pct"] or 0,
    )[:5]
    pb_expansion = sorted(
        [r for r in rows if _finite_change(r, "pb_change_pct")],
        key=lambda r: -(r["pb_change_pct"] or 0),
    )[:5]
    pb_compression = sorted(
        [r for r in rows if _finite_change(r, "pb_change_pct")],
        key=lambda r: r["pb_change_pct"] or 0,
    )[:5]

    return {
        "ok": True,
        "companies": len(rows),
        "valuation_date": universe.get("valuation_date"),
        "averages": {
            "pe": _median(pe_series),
            "pb": _median(pb_series),
            "ev_ebitda": _median(ev_series),
            "dividend_yield": _median(div_series),
        },
        "extremes": {
            "cheapest_sector": {"sector": cheapest_sector, "median_pe": sector_pe.get(cheapest_sector)} if cheapest_sector else None,
            "most_expensive_sector": {"sector": expensive_sector, "median_pe": sector_pe.get(expensive_sector)} if expensive_sector else None,
            "cheapest_industry": {"industry": cheapest_industry, "median_pe": industry_pe.get(cheapest_industry)} if cheapest_industry else None,
            "most_expensive_industry": {"industry": expensive_industry, "median_pe": industry_pe.get(expensive_industry)} if expensive_industry else None,
            "largest_pe_expansion": _pick(pe_expansion, "pe_change_pct"),
            "largest_pe_compression": _pick(pe_compression, "pe_change_pct"),
            "largest_pb_expansion": _pick(pb_expansion, "pb_change_pct"),
            "largest_pb_compression": _pick(pb_compression, "pb_change_pct"),
        },
        "coverage": {
            "pe": len(pe_series),
            "pb": len(pb_series),
            "ev_ebitda": len(ev_series),
            "pct": round(100.0 * len(pe_series) / len(rows), 1) if rows else 0,
        },
    }


def _pick(rows: list[dict[str, Any]], field: str) -> Optional[dict[str, Any]]:
    if not rows:
        return None
    top = rows[0]
    return {
        "symbol": top.get("symbol"),
        "company_name": top.get("company_name"),
        "sector": top.get("sector"),
        field: top.get(field),
    }


def sector_table(universe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = universe.get("rows") or []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sector = row.get("sector")
        if sector:
            groups.setdefault(str(sector), []).append(row)

    out: list[dict[str, Any]] = []
    for sector, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        dna_counts: dict[str, int] = {}
        for m in members:
            d = m.get("industry_dna") or "general"
            dna_counts[d] = dna_counts.get(d, 0) + 1
        dominant_dna = max(dna_counts, key=dna_counts.get) if dna_counts else None
        lens = lens_for(dominant_dna, sector) or {}
        primary = lens.get("primary_metric") or "pe"
        primary_values = [m.get(primary) for m in members if m.get(primary) is not None]
        # Diagnostic only — median of within-sector peer ranks ≈ 50 by construction.
        peer_pcts = [m.get("percentile") for m in members if m.get("percentile") is not None]
        peer_pct_median = _median(peer_pcts)
        current = _median(primary_values)
        # True sector historical percentile: rank today's sector median in its
        # own median history (HVIE). Never fall back to inventing 50.
        hist_pack = _sector_own_history_percentile(sector, current=current, metric=primary)
        hist_pack = _publishable_history(hist_pack)
        history_years = _history_year_span(hist_pack)
        history_unit = "annual periods" if "capital_iq" in str(hist_pack.get("source") or "").lower() else "market observations"
        hist_pct = hist_pack.get("historical_percentile")
        # Upstox sector benchmark only — do not invent one from peer medians.
        sector_key = {
            "pe": "sector_median_pe",
            "pb": "sector_median_pb",
            "ev_ebitda": "sector_median_ev_ebitda",
            "roe": "sector_median_roe",
        }.get(primary, "sector_median_pe")
        covered = sum(1 for m in members if m.get("provider_coverage"))
        sector_bench = None
        if covered > 0:
            sector_bench = _median([m.get(sector_key) for m in members if m.get(sector_key) is not None])
        # Premium vs Upstox sector benchmark (table column) and vs HVIE history (audit).
        hist_median_level = hist_pack.get("historical_median")
        benchmark_premium = None
        historical_premium = None
        if current is not None and sector_bench:
            benchmark_premium = round(100.0 * (current - sector_bench) / sector_bench, 1)
        if (
            current is not None
            and hist_median_level
            and abs(hist_median_level) >= 0.5
            and hist_pack.get("status") == "OK"
        ):
            raw_hist_premium = 100.0 * (current - hist_median_level) / abs(hist_median_level)
            # Cap display; absurd ratios mean contaminated history.
            if abs(raw_hist_premium) <= 500:
                historical_premium = round(raw_hist_premium, 1)
        # UI "Sector" column shows Upstox benchmark — premium must match that denominator.
        premium = benchmark_premium if sector_bench is not None else historical_premium
        premium_basis = (
            "upstox_sector_benchmark"
            if sector_bench is not None
            else "hvie_sector_history"
            if hist_median_level
            else None
        )
        hist_status = str(hist_pack.get("status") or "")
        if hist_status == "DATA_QUALITY_FAIL":
            opportunity = "History Unreliable"
            range_status = "History Unreliable"
            hist_median_level = None  # do not surface contaminated median
        else:
            opportunity = _opportunity_label(hist_pct)
            range_status = _historical_range_status(hist_pct)
        out.append({
            "sector": sector,
            "companies": len(members),
            "primary_metric": primary,
            "primary_metric_label": lens.get("primary_metric_label") or primary.upper(),
            "current": current,
            "historical_median": hist_median_level if hist_median_level is not None else sector_bench,
            "sector_benchmark": sector_bench,
            "sector_benchmark_source": "upstox" if sector_bench is not None and covered > 0 else None,
            "historical_percentile": round(hist_pct, 1) if hist_pct is not None else None,
            "historical_percentile_status": hist_pack.get("status"),
            "historical_percentile_reason": hist_pack.get("reason"),
            "historical_percentile_source": hist_pack.get("source"),
            "historical_observations": hist_pack.get("observation_count"),
            "historical_years": history_years,
            "historical_observation_label": f"{hist_pack.get('observation_count') or 0} {history_unit}",
            "historical_coverage_pct": round(100.0 * len(primary_values) / len(members), 1) if members else 0,
            "historical_confidence": _history_confidence(
                history_years=history_years,
                coverage_pct=round(100.0 * len(primary_values) / len(members), 1) if members else 0,
                status=hist_pack.get("status"),
            ),
            "historical_window": {
                "first": hist_pack.get("first_observation"),
                "last": hist_pack.get("last_observation"),
            },
            # Kept for DQ / audit — NOT the heatmap KPI.
            "peer_relative_percentile_median": (
                round(peer_pct_median, 1) if peer_pct_median is not None else None
            ),
            "premium_pct": premium,
            "benchmark_premium_pct": benchmark_premium,
            "historical_premium_pct": historical_premium,
            "premium_basis": premium_basis,
            "opportunity": opportunity,
            "historical_range_status": range_status,
            "median_pe": _median([m.get("pe") for m in members]),
            "median_pb": _median([m.get("pb") for m in members]),
            "median_ev_ebitda": _median([m.get("ev_ebitda") for m in members]),
            "median_roe": _median([m.get("roe") for m in members]),
            "median_roa": _median([m.get("roa") for m in members]),
            "median_roce": _median([m.get("roce") for m in members]),
            "upstox_coverage": covered,
            "upstox_coverage_pct": round(100.0 * covered / len(members), 1) if members else 0,
            "valid_primary_count": len(primary_values),
            "excluded_primary_count": max(0, len(members) - len(primary_values)),
        })
    return out


def _sector_own_history_percentile(
    sector: str,
    *,
    current: Optional[float],
    metric: str,
) -> dict[str, Any]:
    """HVIE sector own-history percentile; never invents a mid-pack default."""
    try:
        from historical_valuation_intelligence.sector_percentile import (
            sector_historical_percentile,
        )

        # Banks / financials often use pb as primary — request that series.
        metric_key = metric if metric in {"pe", "pb", "ev_ebitda", "ev_sales", "roe"} else "pe"
        return sector_historical_percentile(
            sector,
            current_median=current,
            metric=metric_key if metric_key != "roe" else "pe",
        )
    except Exception as exc:
        return {
            "historical_percentile": None,
            "status": "UNAVAILABLE",
            "reason": f"sector_history_unavailable:{exc}",
            "observation_count": 0,
            "source": None,
        }


def _publishable_history(history: dict[str, Any]) -> dict[str, Any]:
    """Apply a source-aware minimum without discarding annual CapIQ history."""
    pack = dict(history or {})
    obs = int(pack.get("observation_count") or 0)
    source = str(pack.get("source") or "").lower()
    annual_source = "capital_iq" in source or "capiq" in source or "annual" in source
    daily_market_source = not source or "historical_valuation" in source or "reconstructed" in source
    minimum = (
        MIN_ANNUAL_HISTORY_OBS if annual_source
        else MIN_DAILY_HISTORY_OBS if daily_market_source
        else MIN_GENERIC_HISTORY_OBS
    )
    # A data source can provide explicit year depth.  Treat annual points as
    # one observation per financial year; for market series retain the
    # established 24-observation floor.
    years = pack.get("history_years")
    if years is None and annual_source:
        years = obs
    pack["history_years"] = years
    if pack.get("status") == "OK" and obs < minimum:
        pack.update({
            "historical_percentile": None,
            "historical_median": None,
            "sufficient": False,
            "status": "INSUFFICIENT_HISTORY",
            "reason": (
                f"Limited verified sector history — observed {obs} points; need ≥{minimum} "
                f"for this {'annual' if annual_source else 'market-series'} source."
            ),
        })
    return pack


def _history_confidence(*, history_years: Any, coverage_pct: float, status: Any) -> str:
    """Confidence convention from the AGI sector-intelligence methodology."""
    if str(status or "") != "OK":
        return "Insufficient"
    try:
        years = float(history_years or 0)
    except (TypeError, ValueError):
        years = 0
    if coverage_pct >= 70 and years >= 7:
        return "High"
    if coverage_pct >= 40 and years >= 4:
        return "Medium"
    if coverage_pct >= 20 and years >= 2:
        return "Low"
    return "Insufficient"


def _history_year_span(history: dict[str, Any]) -> float:
    """Return actual calendar-year depth; never mistake observations for years."""
    explicit = history.get("history_years")
    try:
        if explicit is not None:
            return round(float(explicit), 1)
    except (TypeError, ValueError):
        pass
    first, last = history.get("first_observation"), history.get("last_observation")
    try:
        start = date.fromisoformat(str(first)[:10])
        end = date.fromisoformat(str(last)[:10])
        return round(max(0.0, (end - start).days / 365.25), 1)
    except (TypeError, ValueError):
        return 0.0


def _historical_range_status(hist_pct: Optional[float]) -> str:
    """Institutional range label — not buy/sell opportunity language."""
    if hist_pct is None:
        return "Coverage Developing"
    if hist_pct <= 25:
        return "Below Historical Range"
    if hist_pct >= 75:
        return "Above Historical Range"
    return "Within Historical Range"


def _opportunity_label(hist_pct: Optional[float]) -> str:
    """Legacy alias — maps to range status for backward compatibility."""
    return _historical_range_status(hist_pct)


def industry_table(universe: dict[str, Any], *, limit: int = 80) -> list[dict[str, Any]]:
    rows = universe.get("rows") or []
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        industry = row.get("industry")
        if industry:
            groups.setdefault(str(industry), []).append(row)

    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:limit]
    out = []
    for rank, (industry, members) in enumerate(ranked, start=1):
        pe_vals = [m.get("pe") for m in members if m.get("pe") is not None]
        # Do not publish peer-rank medians as "historical_percentile" — they
        # collapse to ~50 by construction. Industry own-history is not yet wired.
        out.append({
            "industry": industry,
            "sector": members[0].get("sector") if members else None,
            "companies": len(members),
            "current_pe": _median(pe_vals),
            "historical_percentile": None,
            "historical_percentile_status": "UNAVAILABLE",
            "historical_percentile_reason": "Industry own-history series not yet persisted",
            "peer_relative_percentile_median": _median(
                [m.get("percentile") for m in members if m.get("percentile") is not None]
            ),
            "industry_rank": rank,
            "peer_count": len(members),
            "coverage": len(pe_vals),
        })
    return out


def sector_heatmap(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Color bands by historical valuation percentile."""
    out = []
    for s in sectors:
        pct = s.get("historical_percentile")
        band = "grey"
        if pct is not None:
            if pct <= 20:
                band = "dark_green"
            elif pct <= 45:
                band = "light_green"
            elif pct <= 55:
                band = "grey"
            elif pct <= 80:
                band = "orange"
            else:
                band = "dark_red"
        out.append({**s, "heatmap_band": band})
    return out
