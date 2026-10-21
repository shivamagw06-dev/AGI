"""CAE ranking, dedupe, compression and token budget enforcement."""

from __future__ import annotations

import re
from typing import Any

from app.cae.config import (
    CRITICAL_CHAR_CAP,
    CRITICAL_ITEM_CAP,
    DEFAULT_TOKEN_BUDGET,
    IMPORTANT_CHAR_CAP,
    IMPORTANT_ITEM_CAP,
    OPTIONAL_CHAR_CAP,
    OPTIONAL_ITEM_CAP,
    RANK_WEIGHTS,
)
from app.cae.models import RankedItem

_CRITICAL_KINDS = {"evidence", "conflict", "investment", "event", "forecast"}
_OPTIONAL_KINDS = {"open_intelligence", "knowledge"}


def score_item(item: RankedItem, *, query: str, intents: list[str]) -> float:
    q = (query or "").lower()
    title = (item.title or "").lower()
    relevance = item.relevance
    if not relevance:
        relevance = 0.35
        if any(tok in title for tok in q.split() if len(tok) > 2):
            relevance += 0.35
        if item.kind in intents or any(item.kind in i for i in intents):
            relevance += 0.15
        if item.engine == "eve" and "evidence" in str(intents):
            relevance += 0.1
    relevance = min(1.0, relevance)
    item.relevance = relevance

    w = RANK_WEIGHTS
    score = (
        w["relevance"] * relevance
        + w["freshness"] * item.freshness
        + w["confidence"] * item.confidence
        + w["evidence_quality"] * item.evidence_quality
        + w["forecast_accuracy"] * item.forecast_accuracy
        + w["event_severity"] * item.event_severity
        + w["source_trust"] * item.source_trust
        + w["knowledge_quality"] * item.knowledge_quality
    )
    # Intent boosts
    if "risk" in intents and item.kind == "risk":
        score += 0.08
    if "forecast" in intents and item.kind == "forecast":
        score += 0.08
    if "event" in intents and item.kind == "event":
        score += 0.08
    if "investment_thesis" in intents and item.kind == "investment":
        score += 0.08
    item.ranking_score = round(min(1.0, score), 4)
    return item.ranking_score


def assign_priority(item: RankedItem, *, intents: list[str]) -> str:
    if item.kind == "conflict":
        item.priority = "critical"
        return item.priority
    if item.kind in {"evidence", "investment"} and item.ranking_score >= 0.55:
        item.priority = "critical"
        return item.priority
    if item.kind == "event" and item.event_severity >= 0.7:
        item.priority = "critical"
        return item.priority
    if item.kind == "forecast" and ("forecast" in intents or item.ranking_score >= 0.6):
        item.priority = "important"
        return item.priority
    if item.kind in _CRITICAL_KINDS and item.ranking_score >= 0.45:
        item.priority = "important"
        return item.priority
    if item.kind in _OPTIONAL_KINDS or item.ranking_score < 0.4:
        item.priority = "optional"
        return item.priority
    item.priority = "important"
    return item.priority


def dedupe(items: list[RankedItem]) -> tuple[list[RankedItem], int]:
    seen: dict[str, RankedItem] = {}
    removed = 0
    for item in items:
        key = item.dedupe_key or f"{item.engine}:{item.kind}:{_norm(item.title)}"
        # also soft-merge near-identical titles across engines
        soft = f"{item.kind}:{_norm(item.title)[:60]}"
        existing = seen.get(key) or seen.get(soft)
        if existing:
            removed += 1
            # keep higher score; merge confidence
            if item.ranking_score > existing.ranking_score:
                item.confidence = max(item.confidence, existing.confidence)
                item.why_included = existing.why_included + f"; merged from {existing.engine}"
                seen[key] = item
                seen[soft] = item
            else:
                existing.confidence = max(existing.confidence, item.confidence)
                existing.source_trust = max(existing.source_trust, item.source_trust)
                existing.why_included += f"; confirmed by {item.engine}"
            continue
        seen[key] = item
        seen[soft] = item
    # unique by item_id
    out = []
    ids = set()
    for it in seen.values():
        if it.item_id in ids:
            continue
        ids.add(it.item_id)
        out.append(it)
    out.sort(key=lambda x: -x.ranking_score)
    return out, removed


def compress_item(item: RankedItem) -> RankedItem:
    """Summarise low-priority objects; keep fidelity for critical kinds."""
    if item.priority == "critical" or item.kind in {"evidence", "conflict", "forecast"}:
        return item
    content = item.content
    if isinstance(content, dict):
        keep_keys = ("id", "label", "title", "snippet", "confidence", "score", "status", "metric", "predicted_value", "event_type", "severity")
        slim = {k: content.get(k) for k in keep_keys if k in content}
        if not slim:
            slim = {"summary": str(content)[:240]}
        item.content = slim
        item.compressed = True
        item.token_estimate = max(1, len(str(slim)) // 4)
    elif isinstance(content, str) and len(content) > 280:
        item.content = content[:280] + "…"
        item.compressed = True
        item.token_estimate = max(1, len(item.content) // 4)
    return item


def apply_token_budget(
    items: list[RankedItem],
    *,
    budget: int = DEFAULT_TOKEN_BUDGET,
    compress: bool = True,
) -> tuple[list[RankedItem], dict[str, Any], float]:
    """Enforce priority caps and token budget. Returns kept items, usage, compression_ratio."""
    critical = [i for i in items if i.priority == "critical"][:CRITICAL_ITEM_CAP]
    important = [i for i in items if i.priority == "important"][:IMPORTANT_ITEM_CAP]
    optional = [i for i in items if i.priority == "optional"][:OPTIONAL_ITEM_CAP]

    if compress:
        important = [compress_item(i) for i in important]
        optional = [compress_item(i) for i in optional]

    def _cap_chars(rows: list[RankedItem], char_cap: int) -> list[RankedItem]:
        kept = []
        used = 0
        for r in rows:
            size = len(str(r.content))
            if used + size > char_cap and kept:
                continue
            kept.append(r)
            used += size
        return kept

    critical = _cap_chars(critical, CRITICAL_CHAR_CAP)
    important = _cap_chars(important, IMPORTANT_CHAR_CAP)
    optional = _cap_chars(optional, OPTIONAL_CHAR_CAP)

    ordered = critical + important + optional
    kept: list[RankedItem] = []
    tokens = 0
    for item in ordered:
        est = item.token_estimate or max(1, len(str(item.content)) // 4)
        if tokens + est > budget and kept:
            continue
        kept.append(item)
        tokens += est

    raw_tokens = sum(i.token_estimate or max(1, len(str(i.content)) // 4) for i in items) or 1
    compression_ratio = round(min(1.0, tokens / raw_tokens), 4)
    usage = {
        "budget": budget,
        "total_estimate": tokens,
        "critical": sum(i.token_estimate for i in kept if i.priority == "critical"),
        "important": sum(i.token_estimate for i in kept if i.priority == "important"),
        "optional": sum(i.token_estimate for i in kept if i.priority == "optional"),
        "items_kept": len(kept),
        "items_input": len(items),
    }
    return kept, usage, compression_ratio


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())
