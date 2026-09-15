"""Persistent Company Memory — incremental updates only."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_layer.schema import (
    COMPANY_MEMORY_SLOTS,
    empty_company_memory,
    now_ts,
)
from institutional_knowledge_layer import store


def _uniq_extend(dst: list[Any], src: list[Any], *, limit: int = 40) -> list[Any]:
    out = list(dst or [])
    seen = {str(x).strip().lower() for x in out if x is not None}
    for item in src or []:
        if item is None:
            continue
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out[:limit]


def read_company_memory(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").strip().upper()
    if not t:
        return None
    return store.load_memory("company", t)


def merge_company_extraction(
    ticker: str,
    extraction: dict[str, Any],
    *,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Incrementally merge extracted slots into company memory. Never rebuilds."""
    t = (ticker or "").strip().upper()
    if not t:
        return {"ok": False, "error": "missing_ticker"}

    mem = read_company_memory(t) or empty_company_memory(t)
    slots = mem.setdefault("slots", {})
    for s in COMPANY_MEMORY_SLOTS:
        slots.setdefault(s, [] if s != "identity" else {"ticker": t})

    bag = (extraction or {}).get("slots") or {}
    conf = float((extraction or {}).get("confidence") or 0.0)

    identity = slots.get("identity") if isinstance(slots.get("identity"), dict) else {"ticker": t}
    identity["ticker"] = t
    if bag.get("companies"):
        identity["aliases"] = _uniq_extend(list(identity.get("aliases") or []), bag["companies"], limit=12)
    slots["identity"] = identity

    slots["products_services"] = _uniq_extend(slots.get("products_services") or [], bag.get("products") or [])
    slots["revenue_segments"] = _uniq_extend(slots.get("revenue_segments") or [], bag.get("segments") or [])
    slots["geographic_exposure"] = _uniq_extend(
        slots.get("geographic_exposure") or [], bag.get("countries") or []
    )
    slots["competitive_position"] = _uniq_extend(
        slots.get("competitive_position") or [], bag.get("competitors") or []
    )
    slots["management_timeline"] = _uniq_extend(
        slots.get("management_timeline") or [], bag.get("management") or [], limit=20
    )
    slots["historical_kpis"] = _uniq_extend(
        slots.get("historical_kpis") or [], bag.get("financial_kpis") or [], limit=30
    )
    slots["key_risks"] = _uniq_extend(slots.get("key_risks") or [], bag.get("risks") or [])
    slots["investment_highlights"] = _uniq_extend(
        slots.get("investment_highlights") or [], bag.get("opportunities") or []
    )
    slots["industry_relationships"] = _uniq_extend(
        slots.get("industry_relationships") or [], bag.get("industries") or [], limit=12
    )
    slots["macro_exposure"] = _uniq_extend(
        slots.get("macro_exposure") or [], bag.get("commodities") or [], limit=12
    )
    slots["latest_guidance"] = _uniq_extend(
        slots.get("latest_guidance") or [], bag.get("guidance") or [], limit=12
    )
    slots["valuation_drivers"] = _uniq_extend(
        slots.get("valuation_drivers") or [], bag.get("themes") or [], limit=16
    )

    if not slots.get("business_model") and bag.get("segments"):
        slots["business_model"] = [
            f"Segment exposure includes: {', '.join(str(x) for x in (bag.get('segments') or [])[:4])}"
        ]

    timeline = list(slots.get("document_timeline") or [])
    sid = source_id or (extraction or {}).get("source_id")
    title = (extraction or {}).get("title")
    if sid or title:
        entry = {
            "source_id": sid,
            "title": title,
            "source_type": (extraction or {}).get("source_type"),
            "at": now_ts(),
            "confidence": conf,
        }
        # de-dupe by source_id
        if not any(e.get("source_id") == sid and sid for e in timeline):
            timeline.append(entry)
        slots["document_timeline"] = timeline[-80:]

    prev_conf = float(slots.get("evidence_confidence") or 0.0)
    n = int(mem.get("update_count") or 0) + 1
    slots["evidence_confidence"] = round(min(0.98, (prev_conf * (n - 1) + conf) / max(1, n)), 3)
    slots["last_updated"] = now_ts()

    if sid:
        srcs = list(mem.get("source_ids") or [])
        if sid not in srcs:
            srcs.append(sid)
        mem["source_ids"] = srcs[-200:]

    mem["update_count"] = n
    mem["updated_at"] = now_ts()
    mem["slots"] = slots
    ok = store.save_memory("company", t, mem)
    return {"ok": ok, "ticker": t, "update_count": n, "confidence": slots["evidence_confidence"]}
