"""Derive primitives-only metrics. Never store PE/ROIC/margins unless derived."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def derive_bhavcopy(rows: List[Dict[str, Any]], *, as_of: Optional[str] = None) -> Dict[str, Any]:
    """Derive return_1d, turnover_ratio, liquidity tags from OHLC primitives."""
    derived_rows: List[Dict[str, Any]] = []
    for r in rows:
        ticker = (r.get("ticker") or r.get("symbol") or "").upper() or None
        close = float(r.get("close") or 0)
        prev = float(r.get("prev_close") or 0)
        vol = float(r.get("volume") or 0)
        value = float(r.get("value") or 0)
        ret = r.get("return_1d")
        if ret is None and prev > 0 and close > 0:
            ret = (close / prev) - 1.0
        turnover_ratio = (value / close) if close > 0 else None
        liquidity = "UNKNOWN"
        if vol >= 1_000_000:
            liquidity = "HIGH"
        elif vol >= 100_000:
            liquidity = "MEDIUM"
        elif vol > 0:
            liquidity = "LOW"
        derived_rows.append(
            {
                **r,
                "ticker": ticker,
                "symbol": ticker or r.get("symbol"),
                "return_1d": ret,
                "turnover_ratio": turnover_ratio,
                "liquidity_bucket": liquidity,
                "trade_date": r.get("date") or r.get("trade_date") or as_of,
                "derived_from": ["close", "prev_close", "volume", "value"],
                "derived_at": _now(),
            }
        )
    return {
        "producer": "lidi.derived.bhavcopy",
        "as_of": as_of or _now()[:10],
        "row_count": len(derived_rows),
        "rows": derived_rows,
        "forbidden_stored_metrics": ["PE", "ROIC", "margins", "growth", "beta", "volatility"],
        "note": "Only primitives + 1d return / liquidity buckets are produced here.",
    }


def derive_events(rows: List[Dict[str, Any]], *, source: str) -> Dict[str, Any]:
    """Normalize event rows into Corporate Event knowledge shapes (no new object types)."""
    events = []
    for r in rows:
        ticker = (r.get("ticker") or r.get("symbol") or "").upper() or "UNKNOWN"
        events.append(
            {
                "object_type": "CORPORATE_EVENT",
                "ticker": ticker,
                "symbol": ticker,
                "event_type": r.get("event_type")
                or r.get("action_type")
                or r.get("category")
                or r.get("subject")
                or r.get("purpose")
                or "ANNOUNCEMENT",
                "event_date": r.get("event_date")
                or r.get("ex_date")
                or r.get("effective_date")
                or r.get("announcement_date"),
                "headline": r.get("headline") or r.get("subject") or r.get("purpose") or r.get("action"),
                "details": {
                    "description": r.get("details") or r.get("description") or r.get("purpose"),
                    "security_name": r.get("security_name"),
                    "security_code": r.get("security_code"),
                    "attachment": r.get("attachment"),
                },
                "source": source,
                "derived_from": ["validated_event_row"],
                "derived_at": _now(),
                "fixture": False,
            }
        )
    return {
        "producer": "lidi.derived.events",
        "source": source,
        "object_type": "CORPORATE_EVENT",
        "row_count": len(events),
        "events": events,
    }


def derive_macro(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    observations = []
    for s in series:
        observations.append(
            {
                "object_type": "MACRO",
                "series_id": s.get("series_id") or s.get("metric"),
                "label": s.get("label") or s.get("metric"),
                "value": s.get("value"),
                "unit": s.get("unit"),
                "as_of": s.get("as_of"),
                "source": "RBI_DBIE",
                "derived_from": ["validated_macro_series"],
                "derived_at": _now(),
                "fixture": False,
            }
        )
    return {
        "producer": "lidi.derived.macro",
        "object_type": "MACRO",
        "row_count": len(observations),
        "observations": observations,
    }


def derive_ir_filings(filings: List[Dict[str, Any]], *, ticker: str | None = None) -> Dict[str, Any]:
    docs = []
    for f in filings:
        t = (f.get("ticker") or ticker or "").upper() or "UNKNOWN"
        docs.append(
            {
                "object_type": "EXPECTATION"
                if "guidance" in str(f.get("doc_type", "")).lower() or f.get("guidance_mentioned")
                else "COMPANY",
                "ticker": t,
                "doc_type": f.get("doc_type"),
                "title": f.get("title"),
                "url": f.get("url"),
                "period": f.get("period"),
                "published_at": f.get("published_at"),
                "source": "COMPANY_IR",
                "derived_from": ["validated_ir_filing"],
                "derived_at": _now(),
                "fixture": False,
            }
        )
    return {
        "producer": "lidi.derived.company_ir",
        "row_count": len(docs),
        "documents": docs,
    }
