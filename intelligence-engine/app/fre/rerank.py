"""Step 11 — Re-ranker (cross-encoder style lexical+authority scoring)."""

from __future__ import annotations

from typing import Any

from app.fre.authority import normalize_authority
from app.kip.embeddings import tokenize


def rerank(query: str, hits: list[dict[str, Any]], *, top_k: int = 20) -> list[dict[str, Any]]:
    """Re-rank top candidates. Input typically top-100 hybrid hits → top-20."""
    q_tokens = set(tokenize(query))
    scored: list[dict[str, Any]] = []
    for h in hits:
        text = f"{h.get('heading') or ''} {h.get('text') or ''}".lower()
        tokens = set(tokenize(text))
        overlap = len(q_tokens & tokens) / max(1, len(q_tokens))
        authority = normalize_authority(int(h.get("authority") or 2))
        freshness = 0.8 if (h.get("published_at") or "") >= "2026-01-01" else 0.45
        finance_boost = 0.1 if any(
            k in text for k in ("revenue", "margin", "guidance", "eps", "ebitda", "risk", "capex", "filing")
        ) else 0.0
        base = float(h.get("score") or 0)
        final = (
            0.40 * base
            + 0.25 * overlap
            + 0.20 * authority
            + 0.10 * freshness
            + finance_boost
        )
        item = dict(h)
        item["rerank_score"] = round(final, 6)
        item["rank_components"] = {
            "hybrid": round(base, 4),
            "overlap": round(overlap, 4),
            "authority": round(authority, 4),
            "freshness": round(freshness, 4),
            "finance_relevance": finance_boost,
        }
        scored.append(item)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    for i, item in enumerate(scored[:top_k], start=1):
        item["rank"] = i
    return scored[:top_k]
