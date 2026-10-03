"""Historical Sector Knowledge Object."""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.schema import HD_VERSION


def compile_historical_sector(sector: str, members: list[str]) -> dict[str, Any]:
    pe_by_fy: dict[str, list[float]] = {}
    pb_by_fy: dict[str, list[float]] = {}
    roic_by_fy: dict[str, list[float]] = {}
    winners: list[str] = []
    losers: list[str] = []

    for m in members:
        obj = hd_store.get_object("company", m)
        if not obj:
            continue
        val = obj.get("historical_valuation") or {}
        pe = (val.get("PE") or {}).get("points") or {}
        pb = (val.get("PB") or {}).get("points") or {}
        roic = (val.get("ROIC") or {}).get("points") or {}
        for fy, v in pe.items():
            pe_by_fy.setdefault(fy, []).append(float(v))
        for fy, v in pb.items():
            pb_by_fy.setdefault(fy, []).append(float(v))
        for fy, v in roic.items():
            roic_by_fy.setdefault(fy, []).append(float(v))
        risk = obj.get("historical_risk") or {}
        dd = float(risk.get("max_drawdown_pct") or 0)
        if dd < -40:
            losers.append(m)
        elif dd > -15:
            winners.append(m)

    def _median(xs: list[float]) -> float | None:
        if not xs:
            return None
        s = sorted(xs)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0

    hist_pe = {fy: round(_median(vs) or 0.0, 4) for fy, vs in pe_by_fy.items()}
    hist_pb = {fy: round(_median(vs) or 0.0, 4) for fy, vs in pb_by_fy.items()}
    hist_roic = {fy: round(_median(vs) or 0.0, 4) for fy, vs in roic_by_fy.items()}

    obj = {
        "kind": "historical_sector_object",
        "hd_version": HD_VERSION,
        "sector": sector,
        "members": members,
        "historical_median_pe": hist_pe,
        "historical_median_pb": hist_pb,
        "historical_median_roic": hist_roic,
        "historical_winners": winners[:10],
        "historical_losers": losers[:10],
        "historical_cycles": ["gfc_2008", "covid_2020", "rate_hike_2022_23"],
        "historical_macro_drivers": ["rates", "usd_inr", "gdp"],
        "n_members_with_history": sum(1 for m in members if hd_store.get_object("company", m)),
    }
    hd_store.put_object("sector", sector, obj)
    return obj
