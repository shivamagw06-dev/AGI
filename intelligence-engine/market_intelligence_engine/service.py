"""Market Intelligence Engine service — single dashboard contract."""

from __future__ import annotations

from statistics import median
from typing import Any, Optional

from market_intelligence_engine import aggregation, breadth, flows, opportunities, rotation, summary, universe
from market_intelligence_engine.constitution import CONFIDENCE_METHODOLOGY, CONSTITUTION_VERSION, widget_provenance
from market_intelligence_engine.drivers import market_drivers
from market_intelligence_engine.health import market_health_score
from market_intelligence_engine.regime import classify_market_regime
from market_intelligence_engine.validation import validate_dashboard

ENGINE_CODE = "market_intelligence_engine"
VERSION = "2.0"


def health() -> dict[str, Any]:
    wh: dict[str, Any] = {}
    flow: dict[str, Any] = {}
    try:
        from institutional_warehouse.production import coverage as wh_coverage

        wh = wh_coverage() or {}
    except Exception as exc:
        wh = {"error": str(exc)[:200]}
    try:
        flow = flows.institutional_flows() or {}
    except Exception as exc:
        flow = {"coverage": {"error": str(exc)[:200]}}
    return {
        "ok": "error" not in wh,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "constitution": CONSTITUTION_VERSION,
        "data_path": "warehouse → unified_valuation_engine → market_intelligence_engine",
        "companies": wh.get("companies"),
        "warehouse_rows": wh.get("total_rows"),
        "institutional_flow": flow.get("coverage"),
        "warehouse_error": wh.get("error"),
        "reads": ["institutional_warehouse", "valuation_engine", "valuation_terminal.sector_lens"],
    }


def dashboard(*, universe_limit: int = 5000) -> dict[str, Any]:
    """Full market & sector intelligence pack — constitution v2.0."""
    uni = universe.load_universe(limit=universe_limit)
    if not uni.get("ok"):
        return {"ok": False, "error": uni.get("error"), "engine": ENGINE_CODE, "version": VERSION}

    overview = aggregation.market_overview(uni)
    sectors = aggregation.sector_table(uni)
    heatmap = aggregation.sector_heatmap(sectors)
    industries = aggregation.industry_table(uni)
    breadth_pack = breadth.market_breadth()
    if overview.get("companies"):
        breadth_pack["universe_total"] = overview["companies"]
        breadth_pack["not_tracked"] = max(
            0, overview["companies"] - breadth_pack.get("sample_size", 0)
        )
        if overview["companies"]:
            breadth_pack["coverage_pct"] = round(
                100.0 * breadth_pack.get("sample_size", 0) / overview["companies"], 1
            )
    breadth_pack["provenance"] = widget_provenance(
        source="warehouse.daily_market_history",
        table="daily_market_history",
        coverage=breadth_pack.get("coverage"),
        snapshot_date=breadth_pack.get("date"),
    )

    flow_pack = flows.institutional_flows()
    flow_pack["provenance"] = widget_provenance(
        source="warehouse.institutional_flow",
        table="institutional_flow",
        coverage=flow_pack.get("coverage"),
        snapshot_date=flow_pack.get("latest_date"),
    )

    opps = opportunities.detect_opportunities(uni)
    priorities = opportunities.research_priorities(uni, opps)
    rotate = rotation.market_rotation(sectors, uni)
    rotate["provenance"] = widget_provenance(source="market_intelligence_engine.rotation", table="derived")
    explain = rotation.market_explainability(uni)

    regime_pack = classify_market_regime(
        breadth=breadth_pack, flows=flow_pack, sectors=sectors, overview=overview
    )
    health_pack = market_health_score(
        breadth=breadth_pack, flows=flow_pack, overview=overview, sectors=sectors
    )
    drivers_pack = market_drivers(
        sectors=sectors, rotation=rotate, flows=flow_pack, breadth=breadth_pack
    )

    agi_summary = summary.market_summary(
        overview, sectors, breadth_pack, flow_pack, regime=regime_pack, health=health_pack
    )

    pack: dict[str, Any] = {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "constitution": CONSTITUTION_VERSION,
        "overview": overview,
        "market_regime": regime_pack,
        "market_health": health_pack,
        "market_drivers": drivers_pack,
        "breadth": breadth_pack,
        "flows": flow_pack,
        "sectors": sectors,
        "sector_heatmap": heatmap,
        "industries": industries,
        "opportunities": opps,
        "rotation": rotate,
        "research_priorities": priorities,
        "explainability": explain,
        "summary": agi_summary,
        "confidence": {
            "methodology": CONFIDENCE_METHODOLOGY,
            "research_priority_note": "Per-company confidence reflects evidence completeness, not return expectation.",
        },
        "provenance": {
            "valuation": "warehouse.historical_valuation",
            "provider_ratios": "warehouse.valuation_ratios (upstox)",
            "price": "warehouse.daily_market_history",
            "consensus": "warehouse.consensus",
            "flows": flow_pack.get("provenance") or {},
            "formula": ENGINE_CODE,
            "formula_version": VERSION,
            "constitution": CONSTITUTION_VERSION,
        },
        "coverage": {
            "companies": uni.get("count"),
            "valuation_date": uni.get("valuation_date"),
            "breadth_sample": breadth_pack.get("sample_size"),
            "breadth_coverage_pct": breadth_pack.get("coverage_pct"),
            "flow_history": (flow_pack.get("coverage") or {}).get("history"),
            "upstox_ratio_companies": sum(1 for r in (uni.get("rows") or []) if r.get("provider_coverage")),
        },
    }
    pack["validation"] = validate_dashboard(pack)
    return pack


_SECTOR_ALIASES = {
    "it": "Information Technology",
    "tech": "Information Technology",
    "technology": "Information Technology",
    "information technology": "Information Technology",
    "bfsi": "Financials",
    "banks": "Financials",
    "banking": "Financials",
    "financial": "Financials",
    "financials": "Financials",
    "pharma": "Health Care",
    "healthcare": "Health Care",
    "health care": "Health Care",
    "fmcg": "Consumer Staples",
    "staples": "Consumer Staples",
    "consumer staples": "Consumer Staples",
    "discretionary": "Consumer Discretionary",
    "consumer discretionary": "Consumer Discretionary",
    "auto": "Consumer Discretionary",
    "metals": "Materials",
    "materials": "Materials",
    "energy": "Energy",
    "oil": "Energy",
    "utilities": "Utilities",
    "realty": "Real Estate",
    "real estate": "Real Estate",
    "telecom": "Communication Services",
    "communication": "Communication Services",
    "communication services": "Communication Services",
    "industrials": "Industrials",
    "infra": "Industrials",
}



def _rank_within_sector(members: list[dict[str, Any]],
                        lens: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Order a sector by its own primary metric, richest first.

    Computed here rather than read from a stored column: the sector view
    already holds every member, ranking 149 numbers costs nothing, and a value
    derived at read time cannot fall behind the data it describes.

    Companies without the metric keep their place in the payload but sort last
    and are marked, because dropping them would quietly shrink a sector and
    ranking them as zero would put them at one end of it.
    """
    metric = str(lens.get("primary_metric") or "pe")
    label = str(lens.get("primary_metric_label") or metric.upper())

    def value(row: dict[str, Any]) -> Optional[float]:
        raw = row.get(metric) if row.get(metric) is not None else row.get("primary_value")
        try:
            out = float(raw)
        except (TypeError, ValueError):
            return None
        # A negative multiple is not cheap, it is a loss, and ranking it as the
        # cheapest company in the sector is how a screen surfaces the worst
        # business in it as the best opportunity.
        return out if out > 0 else None

    priced = [(value(m), m) for m in members]
    known = sorted([(v, m) for v, m in priced if v is not None], key=lambda pair: -pair[0])
    unknown = [m for v, m in priced if v is None]

    total = len(known)
    ordered: list[dict[str, Any]] = []
    for index, (v, row) in enumerate(known):
        out = dict(row)
        # Percentile within the sector: 100 is the most expensive name in it.
        out["sector_rank"] = index + 1
        out["sector_percentile"] = round(100.0 * (total - index) / total, 1) if total else None
        out["sector_rank_metric"] = metric
        out["sector_rank_value"] = v
        ordered.append(out)
    for row in unknown:
        out = dict(row)
        out["sector_rank"] = None
        out["sector_percentile"] = None
        out["sector_rank_metric"] = metric
        out["sector_rank_value"] = None
        ordered.append(out)

    basis = {
        "metric": metric,
        "metric_label": label,
        "ranked": total,
        "unranked": len(unknown),
        "leaders_meaning": f"highest {label} in the sector",
        "laggards_meaning": f"lowest {label} in the sector",
        "note": ("Ranked on the sector's own primary metric. Market "
                 "capitalisation is not used: it is absent for most of the "
                 "universe, so ordering by it produced an alphabetical list."),
    }
    return ordered, basis

def _resolve_sector_name(sector: str, available: list[str]) -> str:
    raw = str(sector or "").strip()
    if not raw:
        return raw
    by_lower = {str(s).strip().lower(): str(s).strip() for s in available if s}
    if raw in available:
        return raw
    if raw.lower() in by_lower:
        return by_lower[raw.lower()]
    alias = _SECTOR_ALIASES.get(raw.lower())
    if alias and alias in by_lower.values():
        return alias
    if alias and alias.lower() in by_lower:
        return by_lower[alias.lower()]
    # Prefix / contains soft match
    for name in available:
        if raw.lower() in str(name).lower() or str(name).lower() in raw.lower():
            return str(name)
    return raw


def sector_detail(sector: str, *, universe_limit: int = 5000) -> dict[str, Any]:
    uni = universe.load_universe(limit=universe_limit)
    available = sorted({
        str(r.get("sector") or "").strip()
        for r in (uni.get("rows") or [])
        if str(r.get("sector") or "").strip()
    })
    name = _resolve_sector_name(str(sector or "").strip(), available)
    members = [r for r in (uni.get("rows") or []) if str(r.get("sector") or "") == name]
    if not members:
        return {"ok": False, "error": "sector_not_found", "sector": name, "requested": sector}

    from valuation_terminal.sector_lens import lens_for

    dna_counts: dict[str, int] = {}
    for m in members:
        d = m.get("industry_dna") or "general"
        dna_counts[d] = dna_counts.get(d, 0) + 1
    dominant = max(dna_counts, key=dna_counts.get) if dna_counts else None
    lens = lens_for(dominant, name) or {}

    ranked, basis = _rank_within_sector(members, lens)
    # Richest and cheapest on the sector's own yardstick. Both lists were
    # broken and in opposite ways.
    #
    # "leaders" sorted by market_cap, which is null for 92% of the universe -
    # it is only in the price table for the companies Yahoo happened to return,
    # and the largest of those is a 979 million rupee micro-cap. Every key
    # collapsed to 0, so the sort did nothing and the page showed the first
    # eight companies alphabetically while telling the reader they were the
    # largest constituents.
    #
    # "laggards" filtered on the stored percentile, which is written by the
    # formula engine's valuation stage. That stage only runs on import, never
    # after a sweep, so the field is null everywhere and the list was empty in
    # every sector.
    #
    # Both are now ranked from the members already in hand, so they need no
    # pipeline stage and cannot go stale behind the data they describe.
    leaders = ranked[:8]
    # Only companies that actually carry the metric. The unranked ones sit at
    # the end of the list, so reversing the whole thing put a loss-making
    # company at the top of "cheapest" - which is exactly how a screen
    # surfaces the worst business in a sector as its best opportunity.
    laggards = [r for r in reversed(ranked) if r.get("sector_rank") is not None][:8]

    sector_row = next((s for s in aggregation.sector_table(uni) if s["sector"] == name), {})
    research = _sector_research_pack(name, members, sector_row)

    return {
        "ok": True,
        "sector": name,
        "companies": len(members),
        "lens": lens,
        "valuation": sector_row,
        "leaders": leaders,
        "laggards": laggards,
        # Named, because the reader cannot otherwise tell what "leader" means
        # here - and the previous label ("largest constituents first") was not
        # true of what was shown.
        "ranking_basis": basis,
        "distribution": {
            "pe": _distribution([m.get("pe") for m in members]),
            "pb": _distribution([m.get("pb") for m in members]),
            "ev_ebitda": _distribution([m.get("ev_ebitda") for m in members]),
        },
        # This is deliberately a deterministic, evidence-only layer.  The UI
        # may add prose, but these fields remain the shared sector primitive
        # for Ask AGI, valuation and research workflows.
        "research": research,
        "agi_sector_intelligence": _sector_narrative(name, sector_row, lens),
    }


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def _med(values: list[Any]) -> float | None:
    clean = [n for value in values if (n := _num(value)) is not None]
    return round(float(median(clean)), 2) if clean else None


def _sector_research_pack(name: str, members: list[dict[str, Any]], valuation: dict[str, Any]) -> dict[str, Any]:
    """Evidence-backed sector intelligence with partial-coverage disclosure."""
    from historical_valuation_intelligence.sector_percentile import load_sector_median_series

    primary = str(valuation.get("primary_metric") or "pe")
    metric = primary if primary in {"pe", "pb", "ev_ebitda", "ev_sales"} else "pe"
    try:
        history = load_sector_median_series(name, metric=metric)
    except Exception as exc:  # a selected sector must still render without history
        history = {"points": [], "source": None, "error": str(exc)[:160]}
    points = list(history.get("points") or [])
    current = valuation.get("current")
    current_count = sum(1 for row in members if _num(row.get(primary)) is not None)
    coverage_pct = round(100.0 * current_count / len(members), 1) if members else 0.0
    years = len({str(point.get("period") or "")[:4] for point in points if point.get("period")})
    confidence = valuation.get("historical_confidence") or _confidence(coverage_pct, years)

    history_values = [_num(point.get("value")) for point in points]
    history_values = [value for value in history_values if value is not None]
    bands = _bands(history_values)
    valuation_history = {
        "metric": metric,
        "label": valuation.get("primary_metric_label") or metric.upper(),
        "current": current,
        "points": points[-12:],  # chart reads a compact ten-year/quarterly tail
        "periods": len(points),
        "years": years,
        "source": history.get("source"),
        "bands": bands,
        "percentile": valuation.get("historical_percentile"),
        "range_status": valuation.get("historical_range_status"),
    }

    fundamental_fields = [
        ("roe", "ROE"), ("roce", "ROCE"), ("roa", "ROA"),
        ("debt_equity", "Debt / Equity"), ("dividend_yield", "Dividend Yield"),
    ]
    fundamentals = []
    for field, label in fundamental_fields:
        values = [row.get(field) for row in members]
        present = sum(1 for value in values if _num(value) is not None)
        value = _med(values)
        if value is not None:
            fundamentals.append({
                "key": field, "label": label, "current": value,
                "coverage": present, "coverage_pct": round(100.0 * present / len(members), 1),
                "interpretation": _fundamental_state(field, value),
            })

    industries: dict[str, list[dict[str, Any]]] = {}
    for row in members:
        industry = str(row.get("industry") or "Unclassified")
        industries.setdefault(industry, []).append(row)
    industry_rows = []
    for industry, rows in industries.items():
        industry_rows.append({
            "industry": industry,
            "companies": len(rows),
            "median_pe": _med([row.get("pe") for row in rows]),
            "median_pb": _med([row.get("pb") for row in rows]),
            "median_roe": _med([row.get("roe") for row in rows]),
        })
    industry_rows.sort(key=lambda row: (-row["companies"], row["industry"]))

    # Same ranking as leaders and laggards, and for the same reason: sorting
    # by market_cap here produced an alphabetical table under a heading that
    # told the reader it was the largest constituents.
    ranked_members, ranking_basis = _rank_within_sector(members, valuation)
    company_rows = []
    for row in ranked_members:
        company_rows.append({
            "symbol": row.get("symbol"), "company_name": row.get("company_name"),
            "industry": row.get("industry"), "market_cap": row.get("market_cap"),
            "pe": row.get("pe"), "pb": row.get("pb"), "roe": row.get("roe"),
            # Sector-relative, computed here. The stored percentile comes from
            # the formula engine's valuation stage, which does not run after a
            # sweep, so it is null for every company.
            "historical_percentile": row.get("percentile"),
            "sector_percentile": row.get("sector_percentile"),
            "sector_rank": row.get("sector_rank"),
        })

    view = _sector_view(valuation, fundamentals, confidence)
    return {
        "ranking_basis": ranking_basis,
        "snapshot": {
            "companies": len(members), "metric_coverage": current_count,
            "coverage_pct": coverage_pct, "historical_years": years,
            "confidence": confidence, "valuation_date": valuation.get("historical_window", {}).get("last"),
        },
        "view": view,
        "valuation_history": valuation_history,
        "fundamentals": fundamentals,
        "industries": industry_rows[:20],
        "companies": company_rows[:80],
        "methodology": "Valid constituent observations are aggregated; missing company history reduces coverage, not the sector result.",
    }


def _bands(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p10": None, "p25": None, "median": None, "p75": None, "p90": None}
    ordered = sorted(values)
    def at(percentile: float) -> float:
        return round(ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percentile))], 2)
    return {"p10": at(.10), "p25": at(.25), "median": at(.50), "p75": at(.75), "p90": at(.90)}


def _confidence(coverage: float, years: int) -> str:
    if coverage >= 70 and years >= 7:
        return "High"
    if coverage >= 40 and years >= 4:
        return "Medium"
    if coverage >= 20 and years >= 2:
        return "Low"
    return "Insufficient"


def _fundamental_state(field: str, value: float) -> str:
    if field in {"roe", "roce", "roa"}:
        return "Supportive" if value > 12 else "Developing"
    if field == "debt_equity":
        return "Watch" if value > 1.5 else "Controlled"
    return "Context"


def _sector_view(valuation: dict[str, Any], fundamentals: list[dict[str, Any]], confidence: str) -> dict[str, Any]:
    percentile = _num(valuation.get("historical_percentile"))
    valuation_label = "Coverage developing" if percentile is None else "Premium" if percentile >= 75 else "Below historical range" if percentile <= 25 else "Within historical range"
    roe = next((item.get("current") for item in fundamentals if item.get("key") == "roe"), None)
    quality = "Supportive" if _num(roe) is not None and float(roe) >= 12 else "Needs review"
    return {
        "valuation": valuation_label,
        "fundamentals": quality,
        "risk": "Elevated valuation expectations" if percentile is not None and percentile >= 75 else "Evidence coverage" if confidence != "High" else "Monitor sector-specific catalysts",
        "regime": "Premium valuation" if percentile is not None and percentile >= 75 else "Historical discount" if percentile is not None and percentile <= 25 else "Balanced valuation context",
    }


def _distribution(values: list[Any]) -> dict[str, Any]:
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return {"count": 0}
    return {"count": len(clean), "low": clean[0], "high": clean[-1], "median": clean[len(clean) // 2]}


def _sector_narrative(sector: str, row: dict[str, Any], lens: dict[str, Any]) -> str:
    primary = lens.get("primary_metric_label") or row.get("primary_metric_label") or "P/E"
    status = row.get("historical_range_status") or row.get("opportunity") or "mixed"
    pct = row.get("historical_percentile")
    return (
        f"{sector} is led by {primary}. Historical valuation sits "
        f"{status.lower()} (approx. {pct:.0f}th percentile vs sector history). "
        f"This is sector context for research prioritisation, not a recommendation."
        if pct is not None else
        f"{sector} sector intelligence is available with limited historical percentile coverage."
    )
