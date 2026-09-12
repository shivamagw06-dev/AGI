"""Collector data-quality helpers — duplicates, missing fields, provenance."""

from __future__ import annotations

import hashlib
from typing import Any


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def qa_corporate_actions(actions: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    dupes = 0
    missing_date = 0
    missing_purpose = 0
    by_type: dict[str, int] = {}
    for a in actions:
        key = f"{a.get('security_code')}|{a.get('ex_date')}|{a.get('purpose')}"
        if key in seen:
            dupes += 1
        seen.add(key)
        if not a.get("ex_date"):
            missing_date += 1
        if not a.get("purpose"):
            missing_purpose += 1
        t = str(a.get("action_type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "n": len(actions),
        "duplicates": dupes,
        "missing_ex_date": missing_date,
        "missing_purpose": missing_purpose,
        "by_type": by_type,
        "ok": missing_purpose == 0 and len(actions) > 0,
    }


def qa_macro_series(series: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {str(s.get("metric")) for s in series if s.get("metric")}
    missing_value = sum(1 for s in series if s.get("value") is None and s.get("unit") != "qualitative")
    return {
        "n": len(series),
        "metrics": sorted(metrics),
        "missing_numeric_values": missing_value,
        "ok": len(metrics) >= 4,
    }


def qa_documents(docs: list[dict[str, Any]]) -> dict[str, Any]:
    urls = [str(d.get("url") or "") for d in docs]
    dupes = len(urls) - len(set(urls))
    missing_url = sum(1 for u in urls if not u)
    by_type: dict[str, int] = {}
    for d in docs:
        t = str(d.get("doc_type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "n": len(docs),
        "duplicates": max(0, dupes),
        "missing_url": missing_url,
        "by_type": by_type,
        "ok": missing_url == 0,
    }


def qa_price_points(points: list[dict[str, Any]]) -> dict[str, Any]:
    missing = 0
    bad_ts = 0
    prev = None
    out_of_order = 0
    for p in points:
        payload = p.get("payload") or p
        if payload.get("close") is None and payload.get("price") is None:
            missing += 1
        ts = str(p.get("period_end") or p.get("period") or "")
        if not ts:
            bad_ts += 1
        elif prev and ts < prev:
            out_of_order += 1
        prev = ts or prev
    return {
        "n": len(points),
        "missing_price": missing,
        "missing_timestamp": bad_ts,
        "out_of_order": out_of_order,
        "ok": missing == 0 and bad_ts == 0,
    }
