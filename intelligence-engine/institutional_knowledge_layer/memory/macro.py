"""Persistent Macro Memory — topics + industry spillover."""

from __future__ import annotations

import re
from typing import Any

from institutional_knowledge_layer.schema import (
    MACRO_MEMORY_TOPICS,
    empty_macro_memory,
    now_ts,
)
from institutional_knowledge_layer import store

_TOPIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("interest_rates", re.compile(r"\b(interest rate|repo rate|yield|rbi rate)\b", re.I)),
    ("inflation", re.compile(r"\b(inflation|cpi|wpi)\b", re.I)),
    ("gdp", re.compile(r"\b(gdp|growth rate|economic growth)\b", re.I)),
    ("fiscal_policy", re.compile(r"\b(fiscal|budget|deficit|gst)\b", re.I)),
    ("monetary_policy", re.compile(r"\b(monetary|mpc|liquidity)\b", re.I)),
    ("currencies", re.compile(r"\b(rupee|usd|fx|currency|forex)\b", re.I)),
    ("oil", re.compile(r"\b(crude|brent|oil)\b", re.I)),
    ("gold", re.compile(r"\b(gold|bullion)\b", re.I)),
    ("steel", re.compile(r"\b(steel|iron ore)\b", re.I)),
    ("power", re.compile(r"\b(power|electricity|renewable)\b", re.I)),
    ("real_estate", re.compile(r"\b(real estate|housing|property)\b", re.I)),
    ("trade", re.compile(r"\b(export|import|trade deficit|tariff)\b", re.I)),
    ("government_schemes", re.compile(r"\b(pli|subsidy|scheme|incentive)\b", re.I)),
    ("commodities", re.compile(r"\b(commodit|metal|coal)\b", re.I)),
]


def detect_macro_topics(text: str) -> list[str]:
    blob = text or ""
    hits: list[str] = []
    for topic, pat in _TOPIC_PATTERNS:
        if pat.search(blob) and topic not in hits:
            hits.append(topic)
    return hits[:8]


def read_macro_memory(topic: str) -> dict[str, Any] | None:
    key = (topic or "").strip().lower()
    if not key:
        return None
    return store.load_memory("macro", key)


def merge_macro_extraction(
    topic: str,
    extraction: dict[str, Any],
    *,
    source_id: str | None = None,
    affected_industries: list[str] | None = None,
) -> dict[str, Any]:
    key = (topic or "").strip().lower()
    if not key:
        return {"ok": False, "error": "missing_topic"}
    if key not in MACRO_MEMORY_TOPICS and key not in {t for t, _ in _TOPIC_PATTERNS}:
        # still allow unknown topics
        pass

    mem = read_macro_memory(key) or empty_macro_memory(key)
    conf = float((extraction or {}).get("confidence") or 0.0)
    bag = (extraction or {}).get("slots") or {}
    sid = source_id or (extraction or {}).get("source_id")

    events = list(mem.get("events") or [])
    for ev in bag.get("events") or []:
        entry = {"text": ev, "source_id": sid, "at": now_ts(), "confidence": conf}
        if entry["text"] and not any(e.get("text") == entry["text"] for e in events[-20:]):
            events.append(entry)
    for note in list(bag.get("government_policies") or [])[:4]:
        entry = {"text": note, "source_id": sid, "at": now_ts(), "kind": "policy", "confidence": conf}
        if not any(e.get("text") == entry["text"] for e in events[-20:]):
            events.append(entry)
    mem["events"] = events[-80:]

    inds = list(mem.get("affected_industries") or [])
    for ind in list(affected_industries or []) + list(bag.get("industries") or []):
        if ind and ind not in inds:
            inds.append(ind)
    mem["affected_industries"] = inds[:40]

    notes = list(mem.get("notes") or [])
    excerpt = (extraction or {}).get("excerpt")
    if excerpt and excerpt not in notes:
        notes.append(excerpt)
    mem["notes"] = notes[-40:]

    if sid:
        srcs = list(mem.get("source_ids") or [])
        if sid not in srcs:
            srcs.append(sid)
        mem["source_ids"] = srcs[-200:]

    n = int(mem.get("update_count") or 0) + 1
    prev = float(mem.get("evidence_confidence") or 0.0)
    mem["evidence_confidence"] = round(min(0.98, (prev * (n - 1) + conf) / max(1, n)), 3)
    mem["update_count"] = n
    mem["updated_at"] = now_ts()
    mem["last_updated"] = now_ts()
    ok = store.save_memory("macro", key, mem)
    return {
        "ok": ok,
        "topic": key,
        "update_count": n,
        "affected_industries": mem["affected_industries"],
        "confidence": mem["evidence_confidence"],
    }
