"""Merge Valuation Pack into CID so company_analysis / Decision Engine see real multiples."""

from __future__ import annotations

from typing import Any


def merge_valuation_into_dossier(dossier: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    """Soft-attach P2.2 valuation evidence without inventing BUY/SELL or changing gates."""
    if not isinstance(dossier, dict) or not isinstance(pack, dict) or not pack.get("ok"):
        return dossier
    out = dict(dossier)
    val_pack = pack.get("valuation") if isinstance(pack.get("valuation"), dict) else {}
    current = val_pack.get("current") if isinstance(val_pack.get("current"), dict) else (pack.get("current") or {})
    peers = val_pack.get("peers") if isinstance(val_pack.get("peers"), dict) else {}
    hist = val_pack.get("historical") if isinstance(val_pack.get("historical"), dict) else {}
    bands = hist.get("bands") if isinstance(hist.get("bands"), dict) else (pack.get("historical") or {})
    relative = val_pack.get("relative") if isinstance(val_pack.get("relative"), dict) else (pack.get("relative") or {})
    narrative = val_pack.get("narrative") if isinstance(val_pack.get("narrative"), dict) else (pack.get("narrative") or {})

    pe_band = bands.get("pe") if isinstance(bands.get("pe"), dict) else {}
    pe_rel = relative.get("pe") if isinstance(relative.get("pe"), dict) else {}

    valuation = dict(out.get("valuation") or {})
    # Flatten keys consumed by company_analysis.cid_bridge.normalise_valuation
    valuation.update(
        {
            "pe": current.get("pe") if current.get("pe") is not None else valuation.get("pe"),
            "pb": current.get("pb") if current.get("pb") is not None else valuation.get("pb"),
            "forward_pe": current.get("forward_pe") if current.get("forward_pe") is not None else valuation.get("forward_pe"),
            "peg": current.get("peg") if current.get("peg") is not None else valuation.get("peg"),
            "ev_ebitda": current.get("ev_ebitda") if current.get("ev_ebitda") is not None else valuation.get("ev_ebitda"),
            "enterprise_value": current.get("enterprise_value")
            if current.get("enterprise_value") is not None
            else valuation.get("enterprise_value"),
            "market_cap": current.get("market_cap") if current.get("market_cap") is not None else valuation.get("market_cap"),
            "historical_pe": pe_band.get("median") if pe_band.get("median") is not None else valuation.get("historical_pe"),
            "pe_median": pe_band.get("median"),
            "peer_pe": peers.get("median_pe") if peers.get("median_pe") is not None else valuation.get("peer_pe"),
            "sector_pe": peers.get("median_pe"),
            "pe_range": {
                "low": pe_band.get("low"),
                "high": pe_band.get("high"),
                "median": pe_band.get("median"),
                "percentile": pe_band.get("percentile"),
                "window": pe_band.get("window") or "10Y",
            }
            if pe_band
            else valuation.get("pe_range"),
            "historical_range": bands or valuation.get("historical_range"),
            "premium_discount_pct": pe_rel.get("premium_pct"),
            "expected_growth": (val_pack.get("growth") or pack.get("growth") or {}).get("eps_cagr_3y"),
            "confidence": pack.get("confidence"),
            "current": {
                **dict(valuation.get("current") or {}),
                "trailing_pe": current.get("pe"),
                "forward_pe": current.get("forward_pe"),
                "price_to_book": current.get("pb"),
                "price_to_sales": current.get("price_to_sales"),
                "peg": current.get("peg"),
                "ev_ebitda": current.get("ev_ebitda"),
                "enterprise_value": current.get("enterprise_value"),
                "market_cap": current.get("market_cap"),
                "net_debt": current.get("net_debt"),
            },
            "historical": hist or valuation.get("historical"),
            "peers": peers,
            "relative": relative,
            "quality": val_pack.get("quality") or pack.get("quality"),
            "growth": val_pack.get("growth") or pack.get("growth"),
            "narrative": narrative,
            "engine": pack.get("engine"),
            "version": pack.get("version"),
            "freshness": pack.get("freshness"),
            "lineage": pack.get("lineage"),
            "coverage_pct": pack.get("coverage_pct"),
            "missing": False,
            "placeholder": False,
        }
    )
    out["valuation"] = valuation

    # Market data multiples soft-fill
    md = dict(out.get("market_data") or {})
    mult = dict(md.get("valuation_multiples") or {})
    for src_key, dst_key in (
        ("pe", "trailing_pe"),
        ("forward_pe", "forward_pe"),
        ("pb", "price_to_book"),
        ("price_to_sales", "price_to_sales"),
        ("peg", "peg"),
        ("ev_ebitda", "ev_ebitda"),
        ("enterprise_value", "enterprise_value"),
    ):
        if current.get(src_key) is not None and mult.get(dst_key) is None:
            mult[dst_key] = current[src_key]
    md["valuation_multiples"] = mult
    if current.get("market_cap") is not None and md.get("market_cap") is None:
        md["market_cap"] = current["market_cap"]
    if current.get("price") is not None and md.get("current_price") is None:
        md["current_price"] = current["price"]
    out["market_data"] = md

    # Identity peers for company_analysis peer_comparison
    identity = dict(out.get("identity") or {})
    if not identity.get("peers"):
        identity["peers"] = list(peers.get("universe") or [])
    if peers.get("sector") and not identity.get("sector"):
        identity["sector"] = peers.get("sector")
    out["identity"] = identity

    out["valuation_intelligence"] = {
        "enabled": True,
        "ok": True,
        "engine": pack.get("engine"),
        "version": pack.get("version"),
        "workstream_id": "P2.2",
        "coverage_pct": pack.get("coverage_pct"),
        "confidence": pack.get("confidence"),
        "freshness": pack.get("freshness"),
        "cid_summary": pack.get("cid_summary"),
        "stance": pack.get("stance"),
        "observations": pack.get("observations") or [],
        "peer_universe": pack.get("peer_universe"),
        "relative": relative,
        "historical": bands,
        "recommendation_policy": pack.get("recommendation_policy"),
    }

    # Evidence trail
    evidence = list(out.get("evidence") or [])
    for row in pack.get("evidence") or []:
        if isinstance(row, dict):
            evidence.append(row)
    out["evidence"] = evidence[-200:]

    return out
