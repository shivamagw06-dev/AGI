"""Hybrid / keyword / semantic / entity search over the institutional KB."""

from __future__ import annotations

from app.kip.embeddings import cosine, embed_text, tokenize
from app.kip.models import KipChunk, KipDocument, SearchHit, SearchResponse


def search(
    query: str,
    *,
    documents: dict[str, KipDocument],
    chunks: list[KipChunk],
    mode: str = "hybrid",
    limit: int = 10,
    ticker: str | None = None,
    sector: str | None = None,
    theme: str | None = None,
    broker: str | None = None,
    dim: int = 256,
) -> SearchResponse:
    q = (query or "").strip()
    mode_l = (mode or "hybrid").lower()
    q_tokens = set(tokenize(q))
    q_emb = embed_text(q, dim=dim) if q else []

    # Document-level candidate filter
    # Only the current immutable version may participate in retrieval.  Older
    # versions remain in the store for audit/lineage, but must never compete
    # with the latest CMS article when grounding an answer.
    docs = [d for d in documents.values() if d.superseded_by is None]
    if ticker:
        t = ticker.upper()
        docs = [d for d in docs if t in {x.upper() for x in d.investment.tickers}]
    if sector:
        s = sector.lower()
        docs = [d for d in docs if any(s in x.lower() for x in d.investment.sectors)]
    if theme:
        th = theme.lower()
        docs = [d for d in docs if any(th in x.lower() for x in d.investment.themes)]
    if broker:
        b = broker.lower()
        docs = [d for d in docs if b in (d.document.broker or "").lower()]

    allowed = {d.document_id for d in docs}
    active_chunks = [c for c in chunks if c.document_id in allowed] if allowed else []

    if mode_l in {"entity", "company", "sector", "theme", "broker", "timeline"}:
        hits = _entity_hits(docs, mode_l, q, ticker=ticker, sector=sector, theme=theme, broker=broker)
    elif mode_l == "keyword":
        hits = _score_chunks(documents, active_chunks, q_tokens, q_emb, keyword=1.0, semantic=0.0)
    elif mode_l == "semantic":
        hits = _score_chunks(documents, active_chunks, q_tokens, q_emb, keyword=0.0, semantic=1.0)
    else:
        hits = _score_chunks(documents, active_chunks, q_tokens, q_emb, keyword=0.45, semantic=0.55)

    hits.sort(key=lambda h: h.score, reverse=True)
    return SearchResponse(query=q, mode=mode_l, hits=hits[:limit])


def similar_documents(
    document_id: str,
    *,
    documents: dict[str, KipDocument],
    chunks: list[KipChunk],
    limit: int = 10,
) -> SearchResponse:
    src = documents.get(document_id)
    if src is None:
        return SearchResponse(query=document_id, mode="similar", hits=[])
    # average chunk embedding
    src_chunks = [c for c in chunks if c.document_id == document_id]
    if not src_chunks:
        emb = embed_text(src.cleaned_content or src.content)
    else:
        dim = len(src_chunks[0].embedding) or 256
        acc = [0.0] * dim
        for c in src_chunks:
            for i, v in enumerate(c.embedding):
                acc[i] += v
        n = float(len(src_chunks))
        emb = [v / n for v in acc]
    hits = _score_chunks(
        documents,
        [
            c
            for c in chunks
            if c.document_id != document_id
            and (doc := documents.get(c.document_id)) is not None
            and doc.superseded_by is None
        ],
        set(tokenize(src.document.title + " " + (src.knowledge.summary or ""))),
        emb,
        keyword=0.25,
        semantic=0.75,
    )
    hits.sort(key=lambda h: h.score, reverse=True)
    return SearchResponse(query=document_id, mode="similar", hits=hits[:limit])


def _score_chunks(
    documents: dict[str, KipDocument],
    chunks: list[KipChunk],
    q_tokens: set[str],
    q_emb: list[float],
    *,
    keyword: float,
    semantic: float,
) -> list[SearchHit]:
    best: dict[str, SearchHit] = {}
    for c in chunks:
        doc = documents.get(c.document_id)
        if doc is None:
            continue
        kw = _keyword_score(q_tokens, set(c.tokens))
        sem = cosine(q_emb, c.embedding) if q_emb and c.embedding else 0.0
        score = keyword * kw + semantic * sem
        # boost freshness/confidence lightly
        score *= 0.85 + 0.1 * doc.knowledge.freshness + 0.05 * doc.knowledge.confidence
        prev = best.get(doc.document_id)
        if prev is None or score > prev.score:
            best[doc.document_id] = SearchHit(
                document_id=doc.document_id,
                lineage_id=doc.lineage_id,
                version=doc.document.version,
                title=doc.document.title,
                document_type=doc.document.document_type.value,
                score=round(score, 6),
                keyword_score=round(kw, 6),
                semantic_score=round(sem, 6),
                snippet=c.text[:280],
                tickers=list(doc.investment.tickers),
                themes=list(doc.investment.themes),
                freshness=doc.knowledge.freshness,
                confidence=doc.knowledge.confidence,
            )
    return list(best.values())


def _keyword_score(q_tokens: set[str], doc_tokens: set[str]) -> float:
    if not q_tokens:
        return 0.0
    overlap = len(q_tokens & doc_tokens)
    return overlap / float(len(q_tokens))


def _entity_hits(
    docs: list[KipDocument],
    mode: str,
    query: str,
    *,
    ticker: str | None,
    sector: str | None,
    theme: str | None,
    broker: str | None,
) -> list[SearchHit]:
    q = query.lower()
    hits: list[SearchHit] = []
    for d in docs:
        score = 0.0
        if mode == "company" or mode == "entity":
            if ticker and ticker.upper() in {t.upper() for t in d.investment.tickers}:
                score += 1.0
            elif q and any(q in t.lower() for t in d.investment.tickers + d.investment.companies):
                score += 0.8
        if mode == "sector":
            if sector and any(sector.lower() in s.lower() for s in d.investment.sectors):
                score += 1.0
            elif q and any(q in s.lower() for s in d.investment.sectors):
                score += 0.8
        if mode == "theme":
            if theme and any(theme.lower() in t.lower() for t in d.investment.themes):
                score += 1.0
            elif q and any(q in t.lower() for t in d.investment.themes):
                score += 0.8
        if mode == "broker":
            if broker and broker.lower() in (d.document.broker or "").lower():
                score += 1.0
            elif q and q in (d.document.broker or "").lower():
                score += 0.8
        if mode == "timeline":
            score += 0.5 + 0.5 * d.knowledge.freshness
        if score <= 0:
            continue
        hits.append(
            SearchHit(
                document_id=d.document_id,
                lineage_id=d.lineage_id,
                version=d.document.version,
                title=d.document.title,
                document_type=d.document.document_type.value,
                score=round(score, 6),
                snippet=(d.knowledge.summary or d.research.investment_thesis)[:280],
                tickers=list(d.investment.tickers),
                themes=list(d.investment.themes),
                freshness=d.knowledge.freshness,
                confidence=d.knowledge.confidence,
            )
        )
    return hits
