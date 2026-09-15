"""Peer commentary engine — relative narrative, not standalone praise."""

from __future__ import annotations

from typing import Any

from peer_intelligence.benchmarking.engine import benchmarks_for
from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker
from peer_intelligence.resolver.resolve import resolve_peers
from peer_intelligence.trends.engine import trends_for


def commentary_for(ticker: str, *, focus_metrics: list[str] | None = None) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    resolved = resolve_peers(t)
    bench = benchmarks_for(t)
    if not bench.get("found"):
        return {"ticker": t, "found": False, "narrative": ""}

    default_focus = {
        "banks": ["CASA", "NIM", "CET1", "ROE", "GNPA"],
        "fmcg": ["Operating_Margin", "Gross_Margin", "ROIC", "PE", "Revenue_Growth"],
        "it_services": ["EBIT_Margin", "ROIC", "Attrition", "Cash_Conversion", "Revenue_Growth"],
        "consumer_internet": ["Take_Rate", "Contribution_Margin", "Unit_Economics", "Retention"],
    }.get(pack["sector"] if pack else "", ["ROE", "ROIC"])
    focus = focus_metrics or default_focus
    by_m = {c["metric"]: c for c in bench.get("comparisons") or []}

    compared_peers = []
    compared_history = []
    compared_sector = []
    compared_global = []

    for m in focus:
        c = by_m.get(m)
        if not c:
            continue
        compared_peers.append(c["relative_statement"])
        if c.get("vs_own_5y_avg") is not None:
            compared_history.append(
                f"{m}: latest vs own multi-year avg delta {c['vs_own_5y_avg']} (trend {c.get('trend')})."
            )
        compared_sector.append(
            f"{m} at sector percentile {c['percentile']} (median {c['sector_median']})."
        )

    # trajectory narrowing example for banks CASA
    trajectory = _trajectory_insight(t, pack, by_m)

    direct_names = [p["name"] for p in resolved.get("direct") or []]
    global_names = [p["name"] for p in resolved.get("global_leaders") or []]
    if global_names:
        compared_global.append(
            f"Global reference set includes {', '.join(global_names[:5])}; "
            f"cross-border metric comparability remains partial (see missing data)."
        )

    narrative = _compose_narrative(t, pack, by_m, focus, trajectory, direct_names)

    return {
        "ticker": t,
        "found": True,
        "sector": pack["sector"] if pack else None,
        "focus_metrics": focus,
        "compared_with_peers": compared_peers,
        "compared_with_history": compared_history,
        "compared_with_sector": compared_sector,
        "compared_with_global_leaders": compared_global,
        "trajectory_insight": trajectory,
        "narrative": narrative,
        "institutional_rule": (
            "Never write standalone strength claims; always attach peer rank, own history, or sector percentile."
        ),
    }


def _trajectory_insight(ticker: str, pack: dict[str, Any] | None, by_m: dict[str, Any]) -> str:
    if not pack:
        return ""
    if pack["sector"] == "banks" and "CASA" in by_m:
        tr = trends_for(ticker)
        casa_tr = next((x for x in tr.get("trends") or [] if x["metric"] == "CASA"), None)
        # compare HDFC vs ICICI trajectory if present
        icici = None
        for s in pack.get("series") or []:
            if s.get("metric") == "CASA" and s.get("entity") == "ICICIBANK":
                icici = list((s.get("points") or {}).values())
        subj = None
        for s in pack.get("series") or []:
            if s.get("metric") == "CASA" and s.get("entity") == ticker:
                subj = list((s.get("points") or {}).values())
        if subj and icici and len(subj) >= 3 and len(icici) >= 3:
            sub_delta = subj[-1] - subj[0]
            ici_delta = icici[-1] - icici[0]
            if sub_delta < ici_delta:
                return (
                    f"{ticker}'s CASA ranks {by_m['CASA']['peer_rank']} among the peer group; "
                    f"however its trajectory has weakened over the panel window "
                    f"(Δ {sub_delta:.1f}pp) while ICICIBANK has been more stable "
                    f"(Δ {ici_delta:.1f}pp). Competitive advantage appears to be narrowing "
                    f"in trajectory rather than disappearing. Trend label: {casa_tr and casa_tr.get('trend')}."
                )
    if pack["sector"] == "fmcg" and "Operating_Margin" in by_m:
        om = by_m["Operating_Margin"]
        return (
            f"{ticker} operating margin ranks {om['peer_rank']} of {om['peer_n']} among Indian FMCG peers "
            f"and sits at the {om['percentile']}th percentile; consistency vs own history "
            f"(vs 5y avg {om.get('vs_own_5y_avg')}) supports franchise quality claims only when peer-relative."
        )
    return ""


def _compose_narrative(
    ticker: str,
    pack: dict[str, Any] | None,
    by_m: dict[str, Any],
    focus: list[str],
    trajectory: str,
    direct_names: list[str],
) -> str:
    bits = []
    peers = ", ".join(direct_names[:5]) if direct_names else "the peer set"
    bits.append(f"{ticker} is analysed relative to {peers}.")
    for m in focus[:4]:
        c = by_m.get(m)
        if not c:
            continue
        bits.append(c["relative_statement"])
    if trajectory:
        bits.append(trajectory)
    bits.append(
        "Judgement must remain conditional on seed-panel gaps until filing-complete peer history is populated."
    )
    return " ".join(bits)
