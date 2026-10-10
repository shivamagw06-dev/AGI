"""Sector / macro / timeline / portfolio producers."""

from __future__ import annotations

from typing import Any


def produce_sector(sector: str, company_vals: list[dict[str, Any]]) -> dict[str, Any]:
    pe_vals = []
    roic_vals = []
    members = []
    for c in company_vals:
        members.append(c.get("entity"))
        metrics = ((c.get("valuation") or {}).get("metrics") or {})
        pe_pts = (metrics.get("PE") or {}).get("points") or {}
        roic_pts = (metrics.get("ROIC") or {}).get("points") or {}
        if pe_pts:
            pe_vals.append(float(list(pe_pts.values())[-1]))
        if roic_pts:
            roic_vals.append(float(list(roic_pts.values())[-1]))
    pe_vals.sort()
    roic_vals.sort()
    mid = lambda xs: xs[len(xs) // 2] if xs else None  # noqa: E731
    return {
        "sector": sector,
        "members": members,
        "historical_pe_median": mid(pe_vals),
        "median_roic": mid(roic_vals),
        "n_with_pe": len(pe_vals),
        "top_companies": members[:3],
        "bottom_companies": list(reversed(members[-3:])) if members else [],
        "provider": "kf_sector_producer",
        "insufficient": len(pe_vals) == 0,
    }


def produce_macro(series: dict[str, Any]) -> dict[str, Any]:
    repo = float(series.get("repo_rate") or 0)
    cpi = float(series.get("cpi") or 0)
    regime = "neutral"
    if cpi >= 0.06:
        regime = "high_inflation"
    elif repo >= 0.065:
        regime = "high_rates"
    elif repo > 0 and repo <= 0.035:
        regime = "low_rates"
    return {
        "series": series,
        "regime": regime,
        "historical_percentiles": {
            "repo_rate": 60.0 if repo >= 0.06 else 40.0,
            "cpi": 55.0 if cpi >= 0.04 else 35.0,
        },
        "affected_sectors": ["banks", "it_services", "fmcg"],
        "provider": "kf_macro_producer",
    }


def produce_timeline(entity: str, filings: list[dict[str, Any]]) -> dict[str, Any]:
    events = sorted(filings or [], key=lambda r: str(r.get("date") or ""))
    return {
        "entity": entity.upper(),
        "events": events,
        "n": len(events),
        "provider": "kf_timeline_producer",
    }


def produce_portfolio(book: dict[str, Any]) -> dict[str, Any]:
    holdings = book.get("holdings") or []
    return {
        "holdings": holdings,
        "sector_allocation": book.get("sector_allocation") or {},
        "n_holdings": len(holdings),
        "provider": "kf_portfolio_producer",
    }


def produce_peers(entity: str, sector_members: list[str]) -> dict[str, Any]:
    peers = [m for m in sector_members if m != entity.upper()]
    if not peers:
        return {
            "found": False,
            "entity": entity.upper(),
            "insufficient": True,
            "reason": "no_peer_data",
            "peers": [],
            "fabricated": False,
        }
    return {
        "found": True,
        "entity": entity.upper(),
        "peers": peers,
        "insufficient": False,
        "fabricated": False,
        "provider": "kf_peer_producer",
    }
