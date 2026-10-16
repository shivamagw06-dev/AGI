"""Soft collectors for Company Intelligence.

Priority: curated seeds → company_analysis → management packs → Sector DNA → KF objects.
Never fabricates qualitative facts. Callers must mark UNKNOWN when absent.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence.fixtures.seeds import get_seed
from knowledge_factory.company_intelligence.schema import UNKNOWN


def _sector_for(ticker: str) -> str:
    try:
        from knowledge_factory.nifty500_universe import NIFTY_500_SECTOR

        return str(NIFTY_500_SECTOR.get(ticker.upper()) or UNKNOWN)
    except Exception:
        return UNKNOWN


def _warehouse_company(ticker: str) -> dict[str, Any]:
    """Read the effective master row without making warehouse availability fatal."""
    try:
        from institutional_warehouse import store
        result = store.fetch("company_master", filters={"symbol": str(ticker or "").upper()}, limit=1)
        rows = result.get("rows") or []
        return dict(rows[0]) if rows else {}
    except Exception:
        return {}


def _warehouse_peers(ticker: str, limit: int = 20) -> list[str]:
    """Return vendor-backed peer symbols, preserving source order and uniqueness."""
    try:
        from institutional_warehouse import store
        result = store.fetch("peer_relationships", filters={"symbol": str(ticker or "").upper()}, limit=max(1, int(limit)))
        out: list[str] = []
        seen: set[str] = set()
        for row in result.get("rows") or []:
            peer = str(row.get("peer_symbol") or "").strip().upper()
            if peer and peer != str(ticker or "").upper() and peer not in seen:
                out.append(peer)
                seen.add(peer)
        return out
    except Exception:
        return []


def _dna(sector: str) -> dict[str, Any]:
    if not sector or sector == UNKNOWN:
        return {}
    try:
        from knowledge_factory.sector_intelligence.dna.catalog import sector_dna

        return dict(sector_dna(sector) or {})
    except Exception:
        return {}


def _ticker_business(ticker: str) -> dict[str, Any]:
    try:
        from company_analysis.schema import TICKER_BUSINESS

        return dict(TICKER_BUSINESS.get(ticker.upper()) or {})
    except Exception:
        return {}


def _ticker_peers(ticker: str) -> list[str]:
    try:
        from company_analysis.schema import TICKER_PEERS

        return list(TICKER_PEERS.get(ticker.upper()) or ())
    except Exception:
        return []


def _management_pack(ticker: str) -> dict[str, Any]:
    try:
        from management_intelligence.management_profiles.packs import PROFILES

        return dict(PROFILES.get(ticker.upper()) or {})
    except Exception:
        return {}


def _kf_company(ticker: str) -> dict[str, Any]:
    try:
        from knowledge_factory.store import repository as store

        return dict(store.get_object("company", ticker.upper()) or {})
    except Exception:
        return {}


def _sector_peers(ticker: str, sector: str, limit: int = 6) -> list[str]:
    if not sector or sector == UNKNOWN:
        return []
    try:
        from knowledge_factory.nifty500_universe import NIFTY_500_MEMBERS

        peers = [
            m["ticker"]
            for m in NIFTY_500_MEMBERS
            if m.get("sector") == sector and m.get("ticker") != ticker.upper()
        ]
        return peers[:limit]
    except Exception:
        return []


def collect_company_context(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").upper()
    warehouse_company = _warehouse_company(t)
    sector = str(warehouse_company.get("sector") or _sector_for(t) or UNKNOWN)
    seed = get_seed(t)
    return {
        "ticker": t,
        "sector": sector,
        "seed": seed,
        "has_seed": seed is not None,
        "dna": _dna(sector),
        "ticker_business": _ticker_business(t),
        "ticker_peers": _ticker_peers(t),
        "warehouse_company": warehouse_company,
        "warehouse_peers": _warehouse_peers(t),
        "sector_peers": _sector_peers(t, sector),
        "management_pack": _management_pack(t),
        "kf_company": _kf_company(t),
        "sources_priority": [
            "annual_reports",
            "quarterly_reports",
            "investor_presentations",
            "nse_filings",
            "bse_filings",
            "company_website",
            "mca",
            "rbi",
            "sebi",
            "institutional_seed",
            "institutional_sector_prior",
        ],
    }
