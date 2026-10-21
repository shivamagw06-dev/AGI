"""Persistent Industry Memory — incremental updates only."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_layer.schema import (
    INDUSTRY_MEMORY_SLOTS,
    empty_industry_memory,
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


def read_industry_memory(industry: str) -> dict[str, Any] | None:
    key = (industry or "").strip()
    if not key:
        return None
    return store.load_memory("industry", key)


def merge_industry_extraction(
    industry: str,
    extraction: dict[str, Any],
    *,
    source_id: str | None = None,
) -> dict[str, Any]:
    key = (industry or "").strip()
    if not key:
        return {"ok": False, "error": "missing_industry"}

    mem = read_industry_memory(key) or empty_industry_memory(key)
    slots = mem.setdefault("slots", {})
    for s in INDUSTRY_MEMORY_SLOTS:
        slots.setdefault(s, [])

    bag = (extraction or {}).get("slots") or {}
    conf = float((extraction or {}).get("confidence") or 0.0)

    slots["representative_companies"] = _uniq_extend(
        slots.get("representative_companies") or [], bag.get("companies") or [], limit=30
    )
    slots["growth_drivers"] = _uniq_extend(
        slots.get("growth_drivers") or [], bag.get("opportunities") or []
    )
    slots["competitive_dynamics"] = _uniq_extend(
        slots.get("competitive_dynamics") or [], bag.get("competitors") or []
    )
    slots["regulation"] = _uniq_extend(
        slots.get("regulation") or [], bag.get("government_policies") or []
    )
    slots["supply_chain"] = _uniq_extend(
        slots.get("supply_chain") or [],
        list(bag.get("suppliers") or []) + list(bag.get("customers") or []),
        limit=30,
    )
    slots["typical_kpis"] = _uniq_extend(
        slots.get("typical_kpis") or [], bag.get("financial_kpis") or [], limit=24
    )
    slots["current_trends"] = _uniq_extend(
        slots.get("current_trends") or [], bag.get("themes") or []
    )
    slots["macro_sensitivity"] = _uniq_extend(
        slots.get("macro_sensitivity") or [], bag.get("commodities") or [], limit=16
    )

    timeline = list(slots.get("document_timeline") or [])
    sid = source_id or (extraction or {}).get("source_id")
    if sid or (extraction or {}).get("title"):
        entry = {
            "source_id": sid,
            "title": (extraction or {}).get("title"),
            "at": now_ts(),
            "confidence": conf,
        }
        if not any(e.get("source_id") == sid and sid for e in timeline):
            timeline.append(entry)
        slots["document_timeline"] = timeline[-60:]

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
    ok = store.save_memory("industry", key, mem)
    return {"ok": ok, "industry": key, "update_count": n, "confidence": slots["evidence_confidence"]}
