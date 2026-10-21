"""Evidence ranking — confidence, freshness, warehouse completeness, relevance."""

from __future__ import annotations

from typing import Any, Optional


def _freshness_score(item: dict[str, Any]) -> float:
    raw = item.get("freshness") or item.get("as_of") or item.get("timestamp")
    if not raw:
        return 0.4
    text = str(raw).lower()
    if "2026" in text or "2025" in text:
        return 1.0
    if "2024" in text:
        return 0.8
    if "2023" in text:
        return 0.6
    return 0.45


def _confidence_score(item: dict[str, Any]) -> float:
    c = item.get("confidence")
    if isinstance(c, (int, float)):
        return float(c) / 100.0 if float(c) > 1 else float(c)
    return 0.35


def _warehouse_score(item: dict[str, Any]) -> float:
    src = str(item.get("source") or item.get("provider_id") or item.get("layer") or "").lower()
    if any(k in src for k in ("warehouse", "hvie", "uve", "varie", "capiq", "ikt")):
        return 1.0
    if any(k in src for k in ("business_intelligence", "research_intelligence", "forecast")):
        return 0.85
    if "consensus" in src:
        return 0.35  # demote consensus vs AGIB intelligence
    return 0.5


def _relevance_score(item: dict[str, Any], question: str = "") -> float:
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("title", "summary", "text", "snippet", "claim")
    ).lower()
    if not blob:
        return 0.3
    q_tokens = [t for t in (question or "").lower().split() if len(t) > 3][:8]
    if not q_tokens:
        return 0.5
    hits = sum(1 for t in q_tokens if t in blob)
    return min(1.0, 0.35 + 0.12 * hits)


def rank_evidence(
    evidence: list[dict[str, Any]],
    *,
    question: str = "",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return evidence sorted by institutional quality score (desc)."""
    scored: list[tuple[float, dict[str, Any]]] = []
    for raw in evidence or []:
        if not isinstance(raw, dict):
            continue
        score = (
            0.30 * _confidence_score(raw)
            + 0.20 * _freshness_score(raw)
            + 0.25 * _warehouse_score(raw)
            + 0.25 * _relevance_score(raw, question)
        )
        item = dict(raw)
        item["aqe_rank_score"] = round(score, 4)
        scored.append((score, item))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [item for _, item in scored[: max(1, limit)]]
