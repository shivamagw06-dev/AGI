"""Historical query surface — percentiles, regimes, drawdowns, resilience."""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.objects.company import compile_historical_company
from knowledge_factory.historical_depth.producers.derived import produce_derived, produce_risk_momentum
from knowledge_factory.historical_depth.time_travel import compare_as_of, state_as_of


def valuation_during(entity: str, year: int) -> dict[str, Any]:
    """Show valuation during a calendar year (e.g. INFY 2008) — historical evidence only."""
    e = entity.upper()
    # as_of = end of that year for PIT
    as_of = f"{year}-12-31"
    state = state_as_of(e, as_of)
    if not state.get("found"):
        return {
            "found": False,
            "entity": e,
            "year": year,
            "reason": "historical_evidence_unavailable",
            "fabricated": False,
        }
    derived = produce_derived(e, as_of=as_of)
    pe = (derived.get("metrics") or {}).get("PE", {}).get("points") or {}
    # periods overlapping the year (FY09 for 2008 calendar roughly FY09)
    year_points = {k: v for k, v in pe.items() if k.endswith(f"{year % 100:02d}") or k.endswith(f"{(year + 1) % 100:02d}")}
    # Prefer FY matching crisis year: 2008 → FY09 (ends Mar 2009) and FY08
    fy_keys = [f"FY{year % 100:02d}", f"FY{(year + 1) % 100:02d}"]
    selected = {k: pe[k] for k in fy_keys if k in pe}
    if not selected:
        selected = year_points or pe
    return {
        "found": True,
        "entity": e,
        "year": year,
        "as_of": as_of,
        "valuation": selected,
        "all_pe_as_of": pe,
        "source": "historical_evidence_only",
        "point_in_time_integrity": state.get("point_in_time_integrity"),
        "fabricated": False,
    }


def pe_above_percentile(entity: str, percentile: float = 90.0) -> dict[str, Any]:
    e = entity.upper()
    derived = produce_derived(e)
    pct = derived.get("pe_percentiles") or {}
    pe = (derived.get("metrics") or {}).get("PE", {}).get("points") or {}
    hits = [
        {"period": fy, "pe": pe.get(fy), "percentile": pct.get(fy)}
        for fy, p in pct.items()
        if p >= percentile
    ]
    return {
        "found": True,
        "entity": e,
        "percentile_threshold": percentile,
        "periods": hits,
        "n": len(hits),
    }


def largest_crisis_drawdown(entity: str) -> dict[str, Any]:
    e = entity.upper()
    risk = produce_risk_momentum(e)
    regimes = hd_store.get_regimes()
    crises = [r for r in regimes if "crisis" in (r.get("tags") or []) or r.get("regime_id") in {"gfc_2008", "covid_2020"}]
    # Compute drawdown within each crisis window from prices
    prices = (hd_store.get_series("prices", e) or {}).get("records") or []
    crisis_dds = []
    for reg in crises:
        start, end = reg["start"], reg["end"]
        window = [r for r in prices if start <= str(r.get("period_end")) <= end]
        if not window:
            continue
        closes = [float((r.get("payload") or {}).get("adj_close") or 0) for r in window]
        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            peak = max(peak, c)
            dd = c / peak - 1.0 if peak else 0.0
            max_dd = min(max_dd, dd)
        crisis_dds.append(
            {
                "regime_id": reg["regime_id"],
                "name": reg["name"],
                "start": start,
                "end": end,
                "max_drawdown_pct": round(max_dd * 100.0, 4),
            }
        )
    crisis_dds.sort(key=lambda x: x["max_drawdown_pct"])
    worst = crisis_dds[0] if crisis_dds else None
    return {
        "found": bool(worst),
        "entity": e,
        "worst_crisis": worst,
        "all_crises": crisis_dds,
        "lifetime_max_drawdown_pct": risk.get("max_drawdown_pct"),
    }


def performance_across_rate_hiking_cycles(entity: str) -> dict[str, Any]:
    e = entity.upper()
    regimes = [r for r in hd_store.get_regimes() if "rate_hiking" in (r.get("tags") or [])]
    prices = (hd_store.get_series("prices", e) or {}).get("records") or []
    rows = []
    for reg in regimes:
        start, end = reg["start"], reg["end"]
        window = [r for r in prices if start <= str(r.get("period_end")) <= end]
        if len(window) < 2:
            continue
        c0 = float((window[0].get("payload") or {}).get("adj_close") or 0)
        c1 = float((window[-1].get("payload") or {}).get("adj_close") or 0)
        ret = ((c1 / c0) - 1.0) * 100.0 if c0 else 0.0
        rows.append(
            {
                "regime_id": reg["regime_id"],
                "name": reg["name"],
                "start": start,
                "end": end,
                "return_pct": round(ret, 4),
                "months": len(window),
            }
        )
    return {
        "found": len(rows) >= 1,
        "entity": e,
        "rate_hiking_cycles": rows,
        "n_cycles": len(rows),
        "macro_comparison": True,
    }


def valuation_bands(entity: str) -> dict[str, Any]:
    derived = produce_derived(entity)
    pe = list((((derived.get("metrics") or {}).get("PE") or {}).get("points") or {}).values())
    if not pe:
        return {"found": False, "entity": entity.upper(), "reason": "historical_evidence_unavailable"}
    s = sorted(pe)
    def q(p: float) -> float:
        idx = min(len(s) - 1, max(0, int(p / 100.0 * (len(s) - 1))))
        return s[idx]
    return {
        "found": True,
        "entity": entity.upper(),
        "bands": {
            "p10": q(10),
            "p25": q(25),
            "p50": q(50),
            "p75": q(75),
            "p90": q(90),
            "min": s[0],
            "max": s[-1],
        },
        "n": len(s),
    }


def historical_resilience(entity: str) -> dict[str, Any]:
    dd = largest_crisis_drawdown(entity)
    risk = produce_risk_momentum(entity)
    return {
        "entity": entity.upper(),
        "max_drawdown_pct": risk.get("max_drawdown_pct"),
        "worst_crisis": dd.get("worst_crisis"),
        "recovery_hint": "Post-crisis momentum available via price series after trough",
        "found": risk.get("found", False),
    }


# Re-exports for API convenience
__all__ = [
    "valuation_during",
    "pe_above_percentile",
    "largest_crisis_drawdown",
    "performance_across_rate_hiking_cycles",
    "valuation_bands",
    "historical_resilience",
    "state_as_of",
    "compare_as_of",
    "compile_historical_company",
]
