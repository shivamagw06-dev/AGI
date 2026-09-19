"""Lightweight valuation pack persistence via historical_depth when available."""

from __future__ import annotations

from typing import Any


def persist_pack(pack: dict[str, Any]) -> dict[str, Any]:
    ticker = str(pack.get("ticker") or "").upper()
    current = (pack.get("valuation") or {}).get("current") or pack.get("current") or {}
    if not ticker or not current:
        return {"written": 0, "ticker": ticker, "skipped": True}
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record
    except Exception as exc:  # pragma: no cover
        return {"written": 0, "ticker": ticker, "error": str(exc)[:160]}

    as_of = ((pack.get("freshness") or {}).get("as_of") or pack.get("generated_at") or "")[:10]
    if not as_of:
        return {"written": 0, "ticker": ticker, "skipped": True, "reason": "no_as_of"}

    pit = pit_record(
        entity=ticker,
        kind="valuation",
        period=as_of,
        period_end=as_of,
        available_from=as_of,
        payload={
            "pe": current.get("pe"),
            "pb": current.get("pb"),
            "ev_ebitda": current.get("ev_ebitda"),
            "peg": current.get("peg"),
            "forward_pe": current.get("forward_pe"),
            "market_cap": current.get("market_cap"),
            "enterprise_value": current.get("enterprise_value"),
            "peer_median_pe": ((pack.get("valuation") or {}).get("peers") or {}).get("median_pe"),
            "pe_premium_pct": ((pack.get("relative") or {}).get("pe") or {}).get("premium_pct"),
            "stance": pack.get("stance"),
            "source": "valuation_intelligence_p22",
        },
        source="valuation_intelligence_p22",
        confidence=float(pack.get("confidence") or 0.8),
    )
    hd_store.put_series("valuation", ticker, [pit])
    return {"written": 1, "ticker": ticker, "skipped": False}
