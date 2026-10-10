"""Step 1 — Company identification from CID / SIF / curated maps."""

from __future__ import annotations

from typing import Any

from company_analysis.cid_bridge import normalise_business_model
from company_analysis.schema import TICKER_BUSINESS, TICKER_PEERS


def identify_company(
    ticker: str | None,
    *,
    cid: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = (ticker or (cid or {}).get("ticker") or "").upper() or None
    ident = dict((cid or {}).get("identity") or {})
    profile = dict((cid or {}).get("business_profile") or {})
    sif = sif_pkg or {}
    sector_id = (
        ident.get("sector_id")
        or sif.get("sector_id")
        or ((cid or {}).get("sector_framework") or {}).get("sector_id")
        or ""
    )
    sector_name = (
        ident.get("sector")
        or sif.get("sector_name")
        or ((cid or {}).get("sector_framework") or {}).get("sector_name")
        or sector_id
        or "unknown"
    )
    biz = TICKER_BUSINESS.get(t or "", {})
    peers = list(TICKER_PEERS.get(t or "", ()))
    # Prefer dossier peers if present
    dossier_peers = (cid or {}).get("peers") or ident.get("peers") or []
    if isinstance(dossier_peers, list) and dossier_peers:
        peers = [str(p).upper() for p in dossier_peers if p][:8] or peers

    return {
        "ticker": t,
        "company_name": ident.get("company_name") or biz.get("company_name") or t,
        "sector": sector_name,
        "sector_id": sector_id or None,
        "industry": ident.get("industry") or sector_name,
        "peers": peers,
        "business_model": biz.get("business_model") or normalise_business_model(cid) or None,
        "geography": biz.get("geography") or ident.get("geography") or "India",
        "products": biz.get("products") or profile.get("products"),
        "brands": biz.get("brands"),
        "customers": biz.get("customers"),
        "suppliers": biz.get("suppliers") or (cid or {}).get("suppliers"),
        "index_membership": ident.get("index_membership") or [],
        "employees": ident.get("employees") or profile.get("employees"),
        "headquarters": ident.get("headquarters") or profile.get("headquarters"),
        "sources": ["cid.identity", "cid.business_profile", "sif", "company_analysis.maps"],
    }
