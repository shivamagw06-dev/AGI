"""Deterministic evidence ranking — no LLM."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from evidence_retrieval.schema import OFFICIAL_SOURCE_BONUS, RANK_WEIGHTS
from evidence_retrieval.store import utc_now


def rank_evidence(
    items: list[dict[str, Any]],
    *,
    discovery: dict[str, Any],
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    q = (discovery.get("question") or "").lower()
    needed = set(discovery.get("evidence_types_required") or [])
    companies = set(discovery.get("companies") or [])
    day = str(as_of or discovery.get("as_of") or utc_now()[:10])[:10]
    ranked = []
    seen_keys = set()

    for item in items:
        # duplicate penalty key
        key = (
            item.get("evidence_type"),
            item.get("knowledge_object"),
            item.get("document_id") or item.get("title"),
            item.get("checksum") or item.get("evidence_id"),
        )
        dup = key in seen_keys
        seen_keys.add(key)

        scores = {
            "relevance": _relevance(item, q, needed, companies),
            "freshness": _freshness(item, day),
            "confidence": float(item.get("confidence") or 0.5),
            "provenance_quality": _provenance_quality(item),
            "official_source": OFFICIAL_SOURCE_BONUS.get(str(item.get("source") or ""), 0.5),
            "point_in_time_match": _pit(item, day),
            "coverage": 1.0 if item.get("company") in companies or not companies else 0.6,
            "completeness": _completeness(item),
            "consistency": 0.5 if dup else 0.9,
        }
        # contradiction soft: same type opposing titles
        scores["consistency"] *= _contradiction_factor(item, items)

        total = 0.0
        for k, w in RANK_WEIGHTS.items():
            total += w * float(scores.get(k) or 0.0)
        if dup:
            total *= 0.55  # duplicate penalty

        ranked.append(
            {
                **item,
                "rank_scores": {k: round(v, 4) for k, v in scores.items()},
                "rank_score": round(total, 6),
                "duplicate": dup,
                "ranking_engine": "iere_deterministic_v1",
            }
        )

    # Stable sort: score desc, then evidence_id for determinism
    ranked.sort(key=lambda r: (-r["rank_score"], str(r.get("evidence_id") or "")))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return ranked


def _relevance(item: dict[str, Any], q: str, needed: set[str], companies: set[str]) -> float:
    score = 0.4
    et = item.get("evidence_type")
    if et in needed:
        score += 0.35
    title = str(item.get("title") or "").lower()
    payload_txt = str((item.get("payload") or {}).get("text") or "").lower()
    blob = f"{title} {payload_txt}"
    if q:
        tokens = [t for t in q.split() if len(t) > 3][:8]
        hits = sum(1 for t in tokens if t in blob)
        score += min(0.25, 0.05 * hits)
    if item.get("company") in companies:
        score += 0.1
    return min(1.0, score)


def _freshness(item: dict[str, Any], day: str) -> float:
    af = str(item.get("available_from") or "")[:10]
    if not af:
        return 0.4
    try:
        d0 = datetime.fromisoformat(day)
        d1 = datetime.fromisoformat(af)
        age = abs((d0 - d1).days)
        if age <= 7:
            return 1.0
        if age <= 30:
            return 0.85
        if age <= 90:
            return 0.7
        if age <= 365:
            return 0.5
        return 0.3
    except Exception:
        return 0.4


def _provenance_quality(item: dict[str, Any]) -> float:
    score = 0.3
    if item.get("source"):
        score += 0.15
    if item.get("collector"):
        score += 0.1
    if item.get("checksum"):
        score += 0.15
    if item.get("document_id") and item.get("section") is not None:
        score += 0.2
    if item.get("page") is not None:
        score += 0.1
    return min(1.0, score)


def _pit(item: dict[str, Any], day: str) -> float:
    af = str(item.get("available_from") or "")[:10]
    if not af:
        return 0.5
    return 1.0 if af <= day else 0.0  # future should already be filtered


def _completeness(item: dict[str, Any]) -> float:
    payload = item.get("payload")
    if payload is None:
        return 0.2
    if isinstance(payload, dict) and payload:
        return min(1.0, 0.4 + 0.05 * len(payload))
    if isinstance(payload, str) and payload.strip():
        return 0.8
    return 0.3


def _contradiction_factor(item: dict[str, Any], all_items: list[dict[str, Any]]) -> float:
    # Deterministic soft check: opposing guidance words in same company+type
    text = str(item.get("title") or "").lower()
    neg = any(w in text for w in ("cut", "miss", "decline", "weak"))
    pos = any(w in text for w in ("beat", "raise", "strong", "growth"))
    if not (neg or pos):
        return 1.0
    for other in all_items:
        if other is item:
            continue
        if other.get("company") != item.get("company"):
            continue
        if other.get("evidence_type") != item.get("evidence_type"):
            continue
        ot = str(other.get("title") or "").lower()
        if neg and any(w in ot for w in ("beat", "raise", "strong")):
            return 0.75
        if pos and any(w in ot for w in ("cut", "miss", "decline")):
            return 0.75
    return 1.0


def stable_run_seed(question: str, as_of: str | None) -> str:
    return hashlib.sha256(f"{question}|{as_of or ''}".encode()).hexdigest()[:16]
