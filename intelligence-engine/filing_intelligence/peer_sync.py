"""Soft peer integration — upgrade PIL seed panels to live filing panels.

No PIL redesign: overlays filing-origin points onto peer series at read time.
"""

from __future__ import annotations

from typing import Any

from filing_intelligence.flags import is_enabled
from filing_intelligence.pipeline import analyse_ticker

# Tickers FIL can currently refresh into PIL
_SYNC_TICKERS = ("HDFCBANK", "AXISBANK", "ICICIBANK", "NESTLEIND")


def live_panel_for(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"ticker": ticker, "live": False}
    out = analyse_ticker(ticker)
    if not out.get("found"):
        return {"ticker": ticker, "live": False}
    series = {}
    for s in (out.get("history") or {}).get("series") or []:
        series[s["metric"]] = {
            "points": s["points"],
            "sources": s["sources"],
            "data_class": "live_filing",
            "origin": "filing_intelligence",
            "validation": s.get("validation"),
        }
    return {
        "ticker": out["ticker"],
        "live": True,
        "series": series,
        "confidence": out.get("confidence"),
        "doc_count": len(out.get("documents") or []),
    }


def overlay_peer_series(pack: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a PIL pack with FIL live points overlaid where available."""
    if not is_enabled():
        return pack
    out = dict(pack)
    series = [dict(s) for s in pack.get("series") or []]
    refreshed = []
    for ticker in _SYNC_TICKERS:
        panel = live_panel_for(ticker)
        if not panel.get("live"):
            continue
        for metric, payload in (panel.get("series") or {}).items():
            # update matching entity/metric rows
            matched = False
            for s in series:
                if s.get("entity") == ticker and s.get("metric") == metric:
                    merged = dict(s.get("points") or {})
                    merged.update(payload["points"])
                    s["points"] = merged
                    s["data_class"] = "live_filing"
                    s["source"] = f"filing_intelligence:{','.join(sorted(set((payload.get('sources') or {}).values())))}"
                    matched = True
                    refreshed.append(f"{ticker}:{metric}")
            if not matched and ticker in (pack.get("direct_universe") or []):
                series.append(
                    {
                        "metric": metric,
                        "entity": ticker,
                        "unit": "",
                        "points": payload["points"],
                        "source": "filing_intelligence",
                        "data_class": "live_filing",
                    }
                )
                refreshed.append(f"{ticker}:{metric}:new")
    out["series"] = series
    out["filing_sync"] = {
        "enabled": True,
        "refreshed": refreshed,
        "rule": "Seed panel → live filing panel where FIL facts exist",
    }
    return out


def soft_slice_for_pil(ticker: str | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    if ticker:
        return {"filing_intelligence": live_panel_for(ticker)}
    return {
        "filing_intelligence": {
            "enabled": True,
            "sync_tickers": list(_SYNC_TICKERS),
            "rule": "Peer panels must refresh from FIL after new filings",
        }
    }
