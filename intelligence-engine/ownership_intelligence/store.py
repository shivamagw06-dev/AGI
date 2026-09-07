"""Lightweight ownership pack persistence via historical_depth / local store."""

from __future__ import annotations

from typing import Any


def persist_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Persist quarterly ownership series when historical_depth store is available."""
    ticker = str(pack.get("ticker") or "").upper()
    history = list(pack.get("quarter_history") or [])
    if not ticker or not history:
        return {"written": 0, "ticker": ticker, "skipped": True}
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record
    except Exception as exc:  # pragma: no cover
        return {"written": 0, "ticker": ticker, "error": str(exc)[:160]}

    pits = []
    for row in history:
        pe = row.get("period_end")
        if not pe:
            continue
        pits.append(
            pit_record(
                entity=ticker,
                kind="shareholding",
                period=str(row.get("quarter_label") or pe),
                period_end=str(pe)[:10],
                available_from=str(pe)[:10],
                payload={
                    "promoter": row.get("promoter"),
                    "fii": row.get("fii"),
                    "dii": row.get("dii"),
                    "mutual_funds": row.get("mutual_funds"),
                    "insurance": row.get("insurance"),
                    "public": row.get("public"),
                    "pledged": row.get("promoter_pledge_pct"),
                    "promoter_pledge": row.get("promoter_pledge"),
                    "banks": row.get("banks"),
                    "pension": row.get("pension"),
                    "aif": row.get("aif"),
                    "source": row.get("source"),
                },
                source="ownership_intelligence_p23",
                confidence=float(pack.get("confidence") or 0.9),
            )
        )
    if pits:
        hd_store.put_series("shareholding", ticker, pits)
    return {"written": len(pits), "ticker": ticker, "skipped": False}
