"""Steps 9–10 — Embedding + hybrid search (semantic + BM25-ish keyword)."""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Any

from app.fre.models import FreChunk
from app.fre.store import FreStore
from app.kip.embeddings import cosine, embed_text, tokenize

_WORD = re.compile(r"[a-z0-9]{2,}")


def embed_chunk(chunk: FreChunk) -> FreChunk:
    chunk.embedding = embed_text(f"{chunk.heading}\n{chunk.text}", dim=256)
    return chunk


def _bm25_scores(query: str, chunks: list[FreChunk], *, k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    q_tokens = tokenize(query)
    if not q_tokens or not chunks:
        return {}
    docs = [tokenize(c.text) for c in chunks]
    df: Counter[str] = Counter()
    for toks in docs:
        df.update(set(toks))
    n = len(docs)
    avgdl = sum(len(t) for t in docs) / max(1, n)
    scores: dict[str, float] = {}
    for chunk, toks in zip(chunks, docs):
        tf = Counter(toks)
        dl = len(toks) or 1
        score = 0.0
        for term in q_tokens:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * dl / avgdl)
            score += idf * (tf[term] * (k1 + 1)) / denom
        scores[chunk.chunk_id] = score
    # normalize
    mx = max(scores.values()) if scores else 0.0
    if mx > 0:
        scores = {k: v / mx for k, v in scores.items()}
    return scores


def hybrid_search(
    store: FreStore,
    query: str,
    *,
    limit: int = 100,
    company: str | None = None,
    document_type: str | None = None,
    min_authority: int | None = None,
    since: str | None = None,
) -> list[dict[str, Any]]:
    t0 = time.perf_counter()
    q_vec = embed_text(query, dim=256)
    chunks = list(store.chunks.values())
    if company:
        c = company.lower()
        chunks = [ch for ch in chunks if c in (ch.company or "").lower() or c == (ch.symbol or "").lower()]
    if document_type:
        dt = document_type.lower()
        chunks = [ch for ch in chunks if (ch.document_type or "").lower() == dt]
    if min_authority is not None:
        chunks = [ch for ch in chunks if ch.authority >= min_authority]
    if since:
        chunks = [ch for ch in chunks if (ch.published_at or "") >= since]

    bm25 = _bm25_scores(query, chunks)
    ranked: list[dict[str, Any]] = []
    for ch in chunks:
        if not ch.embedding:
            embed_chunk(ch)
        sem = cosine(q_vec, ch.embedding)
        kw = bm25.get(ch.chunk_id, 0.0)
        # Hybrid: 0.55 semantic + 0.45 keyword
        score = 0.55 * sem + 0.45 * kw
        # Authority / freshness soft boosts
        score += 0.03 * (ch.authority / 10.0)
        if ch.published_at and ch.published_at >= "2026-01-01":
            score += 0.02
        ranked.append(
            {
                "chunk_id": ch.chunk_id,
                "document_id": ch.document_id,
                "score": round(score, 6),
                "semantic": round(sem, 6),
                "keyword": round(kw, 6),
                "title": (ch.metadata or {}).get("title"),
                "heading": ch.heading,
                "section": ch.section,
                "page": ch.page,
                "text": ch.text,
                "company": ch.company,
                "symbol": ch.symbol,
                "document_type": ch.document_type,
                "source": ch.source,
                "published_at": ch.published_at,
                "authority": ch.authority,
                "url": (ch.metadata or {}).get("url"),
                "confidence": ch.confidence,
            }
        )
    ranked.sort(key=lambda r: r["score"], reverse=True)
    store.record_latency(search_ms=(time.perf_counter() - t0) * 1000)
    store.metrics.last_query_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    return ranked[:limit]
