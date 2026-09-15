"""Sector derived producers — recompute from company historical depth / KF objects."""

from __future__ import annotations

import math
from typing import Any

from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.macro_map import macro_relationships
from knowledge_factory.sector_intelligence.playbooks.catalog import sector_playbook
from knowledge_factory.sector_intelligence.schema import canonicalize


def _constituents(sector: str) -> list[str]:
    key = canonicalize(sector) or sector
    try:
        from knowledge_factory.fixtures.seed import sector_map

        smap = sector_map()
    except Exception:
        smap = {}
    members = []
    for ticker, sec in smap.items():
        if canonicalize(sec) == key:
            members.append(ticker.upper())
    return sorted(set(members))


def _overlay_provider_metrics(out: dict[str, Any]) -> dict[str, Any]:
    """Prefer live warehouse.valuation_ratios for current PE/PB/ROE/ROCE/EV."""
    try:
        from valuation_ratios.ingest import apply_latest_ratios

        return apply_latest_ratios(out)
    except Exception:
        return out


def _company_metrics(ticker: str) -> dict[str, Any]:
    """Pull latest PE/ROIC/etc from Historical Depth, else KF company object."""
    out: dict[str, Any] = {"ticker": ticker}
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.producers.derived import produce_derived

        obj = hd_store.get_object("company", ticker)
        if obj:
            val = obj.get("historical_valuation") or {}
            pe = (val.get("PE") or {}).get("points") or {}
            pb = (val.get("PB") or {}).get("points") or {}
            roic = (val.get("ROIC") or {}).get("points") or {}
            roe = (val.get("ROE") or {}).get("points") or {}
            ev = (val.get("EV_EBITDA") or {}).get("points") or {}
            out["pe_history"] = pe
            out["pb_history"] = pb
            out["roic_history"] = roic
            out["roe_history"] = roe
            out["ev_ebitda_history"] = ev
            out["pe"] = list(pe.values())[-1] if pe else None
            out["pb"] = list(pb.values())[-1] if pb else None
            out["roic"] = list(roic.values())[-1] if roic else None
            out["roe"] = list(roe.values())[-1] if roe else None
            out["ev_ebitda"] = list(ev.values())[-1] if ev else None
            risk = obj.get("historical_risk") or {}
            out["max_drawdown_pct"] = risk.get("max_drawdown_pct")
            out["history_years"] = (obj.get("coverage") or {}).get("history_years") or len(pe)
            return _overlay_provider_metrics(out)
        # derive on the fly if series exist
        series = hd_store.get_series("financials_annual", ticker)
        if series:
            d = produce_derived(ticker)
            pe = ((d.get("metrics") or {}).get("PE") or {}).get("points") or {}
            out["pe_history"] = pe
            out["pe"] = list(pe.values())[-1] if pe else None
            roic = ((d.get("metrics") or {}).get("ROIC") or {}).get("points") or {}
            out["roic_history"] = roic
            out["roic"] = list(roic.values())[-1] if roic else None
            out["history_years"] = d.get("n_periods") or 0
            return _overlay_provider_metrics(out)
    except Exception:
        pass
    try:
        from knowledge_factory.store import repository as store

        obj = store.get_object("company", ticker) or {}
        metrics = ((obj.get("historical_valuation") or {}).get("metrics") or {})
        pe = (metrics.get("PE") or {}).get("points") or {}
        out["pe_history"] = pe
        out["pe"] = list(pe.values())[-1] if pe else None
        out["history_years"] = len(pe)
    except Exception:
        pass
    return _overlay_provider_metrics(out)


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


def produce_sector_valuation(sector: str, members: list[str] | None = None) -> dict[str, Any]:
    members = members or _constituents(sector)
    rows = [_company_metrics(m) for m in members]
    pe_now = [float(r["pe"]) for r in rows if r.get("pe") is not None]
    # Aggregate historical medians by FY across members
    pe_by_fy: dict[str, list[float]] = {}
    pb_by_fy: dict[str, list[float]] = {}
    roic_by_fy: dict[str, list[float]] = {}
    for r in rows:
        for fy, v in (r.get("pe_history") or {}).items():
            pe_by_fy.setdefault(fy, []).append(float(v))
        for fy, v in (r.get("pb_history") or {}).items():
            pb_by_fy.setdefault(fy, []).append(float(v))
        for fy, v in (r.get("roic_history") or {}).items():
            roic_by_fy.setdefault(fy, []).append(float(v))
    hist_pe = {fy: round(_median(vs) or 0.0, 4) for fy, vs in sorted(pe_by_fy.items())}
    hist_pb = {fy: round(_median(vs) or 0.0, 4) for fy, vs in sorted(pb_by_fy.items())}
    hist_roic = {fy: round(_median(vs) or 0.0, 4) for fy, vs in sorted(roic_by_fy.items())}
    pe_vals = list(hist_pe.values())
    current_median = _median(pe_now) if pe_now else (pe_vals[-1] if pe_vals else None)
    # Percentile of current vs history
    pct = None
    if current_median is not None and pe_vals:
        pct = round(100.0 * sum(1 for x in pe_vals if x <= current_median) / len(pe_vals), 2)
    return {
        "sector": canonicalize(sector) or sector,
        "members": members,
        "n_members": len(members),
        "n_with_pe": len(pe_now),
        "current_median_pe": current_median,
        "historical_median_pe": hist_pe,
        "historical_median_pb": hist_pb,
        "historical_median_roic": hist_roic,
        "current_vs_history_percentile": pct,
        "history_years": max((r.get("history_years") or 0) for r in rows) if rows else 0,
        "insufficient": len(pe_vals) == 0 and not pe_now,
    }


def produce_sector_leadership(sector: str, members: list[str] | None = None) -> dict[str, Any]:
    members = members or _constituents(sector)
    rows = [_company_metrics(m) for m in members]

    def rank(key: str, reverse: bool = True) -> list[dict[str, Any]]:
        scored = [(r["ticker"], r.get(key)) for r in rows if r.get(key) is not None]
        scored.sort(key=lambda x: x[1], reverse=reverse)
        return [{"ticker": t, key: v, "rank": i + 1} for i, (t, v) in enumerate(scored)]

    roic_r = rank("roic")
    pe_r = rank("pe", reverse=False)  # cheaper = better rank for value
    growth_proxy = rank("roe")
    risk_r = [
        {"ticker": r["ticker"], "max_drawdown_pct": r.get("max_drawdown_pct"), "rank": i + 1}
        for i, r in enumerate(
            sorted(
                [r for r in rows if r.get("max_drawdown_pct") is not None],
                key=lambda x: -(x.get("max_drawdown_pct") or -999),  # less negative better
            )
        )
    ]
    leaders = [x["ticker"] for x in roic_r[:3]]
    laggards = [x["ticker"] for x in list(reversed(roic_r))[:3]] if roic_r else []
    return {
        "sector": canonicalize(sector) or sector,
        "leaders": leaders,
        "laggards": laggards,
        "historical_leaders": leaders,
        "historical_laggards": laggards,
        "rankings": {
            "roic": roic_r,
            "valuation_pe_cheap": pe_r,
            "quality_roe": growth_proxy,
            "risk": risk_r,
        },
        "insufficient": len(roic_r) == 0,
    }


def produce_sector_cycle(sector: str, valuation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Heuristic cycle from valuation percentile + DNA maturity."""
    key = canonicalize(sector) or sector
    dna = sector_dna(key)
    valuation = valuation or produce_sector_valuation(key)
    pct = valuation.get("current_vs_history_percentile")
    if pct is None:
        state = "unknown"
    elif pct >= 85:
        state = "peak"
    elif pct >= 65:
        state = "late_cycle"
    elif pct >= 45:
        state = "expansion"
    elif pct >= 25:
        state = "early_cycle"
    elif pct >= 10:
        state = "recovery"
    else:
        state = "contraction"
    return {
        "sector": key,
        "current_cycle": state,
        "valuation_percentile": pct,
        "typical_valuation": "see_historical_median_pe",
        "typical_margins": dna.get("margin_profile"),
        "typical_growth": dna.get("growth_drivers"),
        "typical_roic": "see_historical_median_roic",
        "historical_cycles": [
            {"regime": "gfc_2008", "label": "contraction"},
            {"regime": "covid_2020", "label": "contraction"},
            {"regime": "recovery_2009_10", "label": "recovery"},
            {"regime": "ai_boom_2023_25", "label": "expansion" if key == "it_services" else "late_cycle"},
        ],
        "industry_maturity": dna.get("industry_maturity"),
        "insufficient": pct is None,
    }


def produce_framework_mapping(sector: str) -> dict[str, Any]:
    dna = sector_dna(sector)
    playbook = sector_playbook(sector)
    return {
        "sector": canonicalize(sector) or sector,
        "preferred_frameworks": list(dna.get("preferred_frameworks") or []),
        "alternative_frameworks": list(dna.get("alternative_frameworks") or []),
        "forbidden_frameworks": list(dna.get("forbidden_frameworks") or []),
        "preferred_valuation_playbook": playbook.get("preferred_valuation"),
        "framework_note": playbook.get("framework_note"),
        "dcf_allowed": "traditional_dcf" not in (dna.get("forbidden_frameworks") or [])
        and "traditional_dcf_primary" not in (dna.get("forbidden_frameworks") or []),
        "residual_income_preferred": "residual_income" in (dna.get("preferred_frameworks") or []),
    }


def produce_sector_risk(sector: str, members: list[str] | None = None) -> dict[str, Any]:
    members = members or _constituents(sector)
    rows = [_company_metrics(m) for m in members]
    dds = [float(r["max_drawdown_pct"]) for r in rows if r.get("max_drawdown_pct") is not None]
    return {
        "sector": canonicalize(sector) or sector,
        "median_max_drawdown_pct": _median(dds),
        "worst_member_drawdown_pct": min(dds) if dds else None,
        "n": len(dds),
        "insufficient": not dds,
    }


def produce_cross_sector_rankings(sectors: list[str]) -> dict[str, Any]:
    roic_scores = []
    pe_scores = []
    for s in sectors:
        val = produce_sector_valuation(s)
        med_roic = None
        hist = val.get("historical_median_roic") or {}
        if hist:
            med_roic = list(hist.values())[-1]
        if med_roic is not None:
            roic_scores.append({"sector": s, "roic": med_roic})
        if val.get("current_median_pe") is not None:
            pe_scores.append({"sector": s, "pe": val["current_median_pe"]})
    roic_scores.sort(key=lambda x: -x["roic"])
    pe_scores.sort(key=lambda x: x["pe"])
    return {
        "roic_ranking": [{**r, "rank": i + 1} for i, r in enumerate(roic_scores)],
        "valuation_cheap_ranking": [{**r, "rank": i + 1} for i, r in enumerate(pe_scores)],
        "strongest_roic_sector": roic_scores[0] if roic_scores else None,
    }


def relative_company_vs_sector(ticker: str, sector: str | None = None) -> dict[str, Any]:
    """Is company expensive relative to sector history?"""
    try:
        from knowledge_factory.fixtures.seed import sector_map

        sector = sector or sector_map().get(ticker.upper())
    except Exception:
        pass
    key = canonicalize(sector)
    if not key:
        return {
            "found": False,
            "ticker": ticker.upper(),
            "reason": "sector_history_unavailable",
            "fabricated": False,
            "insufficient": True,
        }
    company = _company_metrics(ticker.upper())
    sector_val = produce_sector_valuation(key)
    pe = company.get("pe")
    hist = list((sector_val.get("historical_median_pe") or {}).values())
    if pe is None or not hist:
        return {
            "found": False,
            "ticker": ticker.upper(),
            "sector": key,
            "reason": "sector_history_unavailable",
            "fabricated": False,
            "insufficient": True,
        }
    pct = round(100.0 * sum(1 for x in hist if x <= pe) / len(hist), 2)
    median = _median(hist)
    premium = ((pe / median) - 1.0) * 100.0 if median else None
    return {
        "found": True,
        "ticker": ticker.upper(),
        "sector": key,
        "company_pe": pe,
        "sector_historical_median_pe": median,
        "company_vs_sector_history_percentile": pct,
        "premium_to_sector_median_pct": round(premium, 2) if premium is not None else None,
        "expensive_vs_history": pct >= 75,
        "evidence": "historical_sector_valuation",
        "fabricated": False,
    }
