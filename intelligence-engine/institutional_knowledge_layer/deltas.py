"""Cross-document intelligence — meaningful deltas only."""

from __future__ import annotations

import re
from typing import Any

from institutional_knowledge_layer.flags import ikl_delta_enabled
from institutional_knowledge_layer.schema import DELTA_KINDS, now_ts
from institutional_knowledge_layer import store

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("management_change", re.compile(r"\b(ceo|cfo|md|chairman|appoint|resign|succeed)\b", re.I)),
    ("guidance_revision", re.compile(r"\b(guidance|outlook|revise|lowered|raised|cut guidance)\b", re.I)),
    ("strategy_change", re.compile(r"\b(strategy|pivot|restructur|new segment|exit)\b", re.I)),
    ("capex_change", re.compile(r"\b(capex|capital expenditure|capacity expansion)\b", re.I)),
    ("risk_change", re.compile(r"\b(risk|headwind|litigation|impairment)\b", re.I)),
    ("business_model_evolution", re.compile(r"\b(business model|platform|subscription|mix shift)\b", re.I)),
    ("margin_change", re.compile(r"\b(margin|ebitda margin|gross margin)\b", re.I)),
    ("capital_allocation_change", re.compile(r"\b(buyback|dividend|acquisition|m&a|debt|buy[- ]back)\b", re.I)),
]


def detect_deltas(
    *,
    ticker: str | None,
    extraction: dict[str, Any],
    prior_extraction: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not ikl_delta_enabled():
        return []
    try:
        text_bits: list[str] = []
        bag = (extraction or {}).get("slots") or {}
        for key in ("guidance", "risks", "events", "financial_kpis", "management", "opportunities"):
            for item in bag.get(key) or []:
                text_bits.append(str(item))
        blob = " ".join(text_bits)
        if not blob.strip():
            return []

        prior_blob = ""
        if prior_extraction:
            pbag = (prior_extraction or {}).get("slots") or {}
            prior_bits = []
            for key in ("guidance", "risks", "events", "financial_kpis", "management"):
                for item in pbag.get(key) or []:
                    prior_bits.append(str(item))
            prior_blob = " ".join(prior_bits)

        out: list[dict[str, Any]] = []
        for kind, pat in _PATTERNS:
            if kind not in DELTA_KINDS:
                continue
            if not pat.search(blob):
                continue
            # Skip if same kind signal already present identically in prior
            if prior_blob and pat.search(prior_blob) and _rough_overlap(blob, prior_blob):
                continue
            snippet = next((s for s in text_bits if pat.search(s)), text_bits[0] if text_bits else "")
            out.append(
                {
                    "kind": kind,
                    "ticker": (ticker or "").upper() or None,
                    "summary": snippet[:280],
                    "source_id": (extraction or {}).get("source_id"),
                    "confidence": float((extraction or {}).get("confidence") or 0.4),
                    "at": now_ts(),
                }
            )
        return out[:12]
    except Exception:
        return []


def _rough_overlap(a: str, b: str) -> bool:
    aa = set(re.findall(r"[a-z0-9]{4,}", (a or "").lower()))
    bb = set(re.findall(r"[a-z0-9]{4,}", (b or "").lower()))
    if not aa or not bb:
        return False
    inter = len(aa & bb)
    return inter / max(1, min(len(aa), len(bb))) > 0.72


def persist_deltas(deltas: list[dict[str, Any]]) -> int:
    n = 0
    for d in deltas or []:
        if store.append_jsonl("deltas", d):
            n += 1
            t = d.get("ticker")
            if t:
                hist = store.load_memory("delta_timeline", str(t).upper()) or {
                    "ticker": str(t).upper(),
                    "deltas": [],
                }
                rows = list(hist.get("deltas") or [])
                rows.append(d)
                hist["deltas"] = rows[-100:]
                hist["updated_at"] = now_ts()
                store.save_memory("delta_timeline", str(t).upper(), hist)
    return n


def timeline_for(ticker: str, *, limit: int = 40) -> list[dict[str, Any]]:
    hist = store.load_memory("delta_timeline", (ticker or "").upper())
    if not hist:
        return []
    rows = list(hist.get("deltas") or [])
    return rows[-max(1, int(limit)) :]
