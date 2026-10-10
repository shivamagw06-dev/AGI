"""Resolve canonical company identity for CID."""

from __future__ import annotations

from typing import Any


def resolve_identity(ticker: str | None, *, query: str | None = None) -> dict[str, Any]:
    """Soft-resolve identity from SIF + AOI registry when available."""
    t = (ticker or "").upper() or None
    out: dict[str, Any] = {
        "company_name": t,
        "nse_symbol": t,
        "bse_code": None,
        "isin": None,
        "sector": None,
        "industry": None,
        "sub_sector": None,
        "sector_id": None,
        "market_cap": None,
        "index_membership": [],
    }
    if not t and not query:
        return out

    # SIF detection
    try:
        from sif.detection import detect_sector
        from sif.frameworks import get_framework

        det = detect_sector(query or t or "", t)
        t = det.get("ticker") or t
        out["nse_symbol"] = t
        out["company_name"] = det.get("company_name") or det.get("name") or t
        out["sector_id"] = det.get("sector_id")
        fw = get_framework(det.get("sector_id"))
        if fw:
            out["sector"] = fw.name
            out["industry"] = fw.sector_id
            out["sub_sector"] = fw.sector_id
    except Exception:
        pass

    # AOI registry enrichment
    if t:
        try:
            from app.aoi.registry import CompanyRegistry

            reg = CompanyRegistry()
            reg.seed_default_universes()
            co = reg.by_symbol(t) if hasattr(reg, "by_symbol") else None
            if co is None and hasattr(reg, "resolve"):
                co = reg.resolve(t)
            if co is not None:
                out["company_name"] = getattr(co, "company_name", None) or out["company_name"]
                out["nse_symbol"] = getattr(co, "nse_symbol", None) or t
                out["isin"] = getattr(co, "isin", None) or out.get("isin")
                out["sector"] = getattr(co, "sector", None) or out.get("sector")
                out["industry"] = getattr(co, "industry", None) or out.get("industry")
                uni = getattr(co, "universe", None)
                if uni:
                    out["index_membership"] = [str(uni)]
        except Exception:
            pass

    out["nse_symbol"] = (out.get("nse_symbol") or t or "").upper() or None
    return out
