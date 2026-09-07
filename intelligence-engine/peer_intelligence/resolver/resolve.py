"""Peer resolution — direct / sector / global / regional / historical leaders."""

from __future__ import annotations

from typing import Any

from peer_intelligence.peer_database.store import find_pack_for_ticker, identity, normalize_ticker


def resolve_peers(ticker: str) -> dict[str, Any]:
    t = normalize_ticker(ticker)
    pack = find_pack_for_ticker(t)
    ident = identity(t)
    if not pack or not ident:
        return {
            "ticker": t,
            "resolved": False,
            "reason": "no_peer_pack",
            "direct": [],
            "sector_leaders": [],
            "global_leaders": [],
            "regional_leaders": [],
            "historical_leaders": [],
        }

    by_tier: dict[str, list[dict[str, Any]]] = {
        "direct": [],
        "sector_leader": [],
        "industry_leader": [],
        "global_leader": [],
        "regional_leader": [],
        "historical_leader": [],
    }
    for i in pack.get("identities") or []:
        if i["ticker"] == t:
            continue
        tier = i.get("tier") or "direct"
        by_tier.setdefault(tier, []).append(i)

    # historical leaders = entities with best long-run metric medians (CASA/ROIC/EBIT)
    historical = _historical_leaders(pack, t)

    return {
        "ticker": t,
        "resolved": True,
        "company": ident,
        "pack_id": pack["pack_id"],
        "sector": pack["sector"],
        "direct": by_tier.get("direct") or [],
        "sector_leaders": by_tier.get("sector_leader") or [],
        "industry_leaders": by_tier.get("industry_leader") or [],
        "global_leaders": by_tier.get("global_leader") or [],
        "regional_leaders": by_tier.get("regional_leader") or [],
        "historical_leaders": historical,
        "direct_universe": pack.get("direct_universe") or [],
        "global_universe": pack.get("global_universe") or [],
        "missing": pack.get("missing") or [],
    }


def _historical_leaders(pack: dict[str, Any], subject: str) -> list[dict[str, Any]]:
    """Pick entities with strongest average of a primary quality metric over history."""
    primary = {
        "banks": "CASA",
        "fmcg": "ROIC",
        "it_services": "EBIT_Margin",
        "consumer_internet": "Unit_Economics",
    }.get(pack.get("sector") or "", "ROE")
    universe = set(pack.get("direct_universe") or [])
    scores: list[tuple[float, str]] = []
    for s in pack.get("series") or []:
        if s.get("metric") != primary or s.get("entity") not in universe:
            continue
        pts = list((s.get("points") or {}).values())
        if not pts:
            continue
        scores.append((sum(pts) / len(pts), s["entity"]))
    scores.sort(reverse=True)
    id_map = {i["ticker"]: i for i in pack.get("identities") or []}
    out = []
    for avg, ticker in scores[:3]:
        if ticker == subject:
            continue
        row = dict(id_map.get(ticker) or {"ticker": ticker})
        row["historical_metric"] = primary
        row["historical_avg"] = round(avg, 2)
        row["tier"] = "historical_leader"
        out.append(row)
    return out
