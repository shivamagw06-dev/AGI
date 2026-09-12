"""RAG evidence packs — priority retrieval; never model memory alone (KIP P0/P1)."""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from app.kip.models import (
    KipDocument,
    RagEvidenceItem,
    RagEvidencePack,
    SearchHit,
    SOURCE_PRIORITY,
)
from app.kip.search import search
from app.kip.sources import retrieval_priority, source_class

_JUNK_TITLES = {
    "hello world",
    "sample private research",
    "test",
    "asdf",
    "lorem ipsum",
    "untitled",
    "demo",
}
_JUNK_TITLE_RE = re.compile(r"^(test|demo|sample|tmp|asdf|xxx)\b", re.I)


def build_evidence_pack(
    query: str,
    *,
    documents: dict[str, KipDocument],
    chunks: list,
    ticker: str | None = None,
    limit: int = 8,
    dim: int = 256,
) -> RagEvidencePack:
    return build_priority_evidence_pack(
        query,
        documents=documents,
        chunks=chunks,
        ticker=ticker,
        limit=limit,
        dim=dim,
    )


def build_priority_evidence_pack(
    query: str,
    *,
    documents: dict[str, KipDocument],
    chunks: list,
    ticker: str | None = None,
    limit: int = 12,
    dim: int = 256,
    engine_states: list[dict[str, Any]] | None = None,
    l4_opinion: dict[str, Any] | None = None,
    portfolio_exposure: dict[str, Any] | None = None,
) -> RagEvidencePack:
    """
    Retrieval order:
      1 AGI research → 2 Engine states → 3 L4 → 4 Broker → 5 News → 6 Filings → 7 General
    """
    result = search(
        query,
        documents=documents,
        chunks=chunks,
        mode="hybrid",
        limit=max(limit * 3, 20),
        ticker=ticker,
        dim=dim,
    )
    # Re-rank by institutional priority then score
    ranked = sorted(
        result.hits,
        key=lambda h: (
            SOURCE_PRIORITY.get(h.document_type, 7),
            -h.score,
        ),
    )[:limit]

    supporting: list[RagEvidenceItem] = []
    conflicting: list[RagEvidenceItem] = []
    sources: list[str] = []
    freshness_vals: list[float] = []
    conf_vals: list[float] = []
    agi_used: list[str] = []
    broker_used: list[str] = []
    news_used: list[str] = []
    filings_used: list[str] = []
    last_updated: _dt.datetime | None = None

    for hit in ranked:
        doc = documents.get(hit.document_id)
        if doc is None or _is_junk_document(doc):
            continue
        item = _to_item(doc, hit)
        sources.append(f"{doc.document.source}:{doc.document.title}")
        freshness_vals.append(doc.knowledge.freshness)
        conf_vals.append(doc.knowledge.confidence)
        if last_updated is None or doc.created_at > last_updated:
            last_updated = doc.created_at
        cls = source_class(doc.document.document_type)
        if cls == "agi_research":
            agi_used.append(doc.document_id)
        elif cls == "broker_research":
            broker_used.append(doc.document_id)
        elif cls == "latest_news":
            news_used.append(doc.document_id)
        elif cls == "company_filings":
            filings_used.append(doc.document_id)

        # Cautious / bearish notes are still supporting evidence for open questions
        # like "how is Indian IT doing?". Only demote true query conflicts here.
        if _conflicts_with_query(query, doc):
            conflicting.append(item)
        else:
            supporting.append(item)

    bulls = [i for i in supporting if i.stance == "bull"]
    bears = [i for i in supporting if i.stance == "bear"]
    # When both bullish and bearish research exist, surface bears as conflicting opinions.
    if bulls and bears:
        for b in bears:
            if b not in conflicting:
                conflicting.append(b)

    freshness = sum(freshness_vals) / len(freshness_vals) if freshness_vals else 0.0
    confidence = sum(conf_vals) / len(conf_vals) if conf_vals else 0.0
    if conflicting and bulls and bears:
        confidence *= 0.75
    # House-view boost when AGI research present
    if agi_used:
        confidence = min(0.98, confidence + 0.05)

    return RagEvidencePack(
        query=query,
        documents_retrieved=[h.document_id for h in ranked],
        supporting_evidence=supporting,
        conflicting_opinions=conflicting,
        source_list=sources,
        agi_research_used=agi_used,
        broker_reports_used=broker_used,
        news_used=news_used,
        filings_used=filings_used,
        engine_evidence=list(engine_states or []),
        l4_opinion=l4_opinion,
        portfolio_exposure=portfolio_exposure,
        freshness_score=round(freshness, 4),
        confidence_score=round(confidence, 4),
        last_updated=last_updated,
        knowledge_version="kip-v1.0.1-p1",
        answer_policy="retrieval_augmented_only",
    )


def research_writer_context(
    *,
    ticker: str | None,
    query: str,
    documents: dict[str, KipDocument],
    chunks: list,
    dim: int = 256,
    engine_states: list[dict[str, Any]] | None = None,
    l4_opinion: dict[str, Any] | None = None,
    portfolio_exposure: dict[str, Any] | None = None,
) -> dict:
    """Retrieve institutional context for AGI research writing (no engine redesign)."""
    from app.kip.client_search import research_continuity_context

    return research_continuity_context(
        ticker=ticker,
        query=query,
        documents=documents,
        chunks=chunks,
        engine_states=engine_states,
        l4_opinion=l4_opinion,
        portfolio_exposure=portfolio_exposure,
        dim=dim,
    )


def _to_item(doc: KipDocument, hit: SearchHit) -> RagEvidenceItem:
    stance = "neutral"
    if doc.research.bull_case and not doc.research.bear_case:
        stance = "bull"
    elif doc.research.bear_case and not doc.research.bull_case:
        stance = "bear"
    elif doc.research.bull_case and doc.research.bear_case:
        stance = "bull" if len(doc.research.bull_case) >= len(doc.research.bear_case) else "bear"
    text_l = (doc.cleaned_content or "").lower()
    if any(w in text_l for w in ("downgrade", "sell", "underweight", "bearish")):
        stance = "bear"
    if any(w in text_l for w in ("upgrade", "buy", "overweight", "bullish")) and stance != "bear":
        stance = "bull"
    return RagEvidenceItem(
        document_id=doc.document_id,
        title=doc.document.title,
        snippet=hit.snippet or (doc.knowledge.summary or doc.research.investment_thesis)[:280],
        tickers=list(doc.investment.tickers),
        stance=stance,
        priority=retrieval_priority(doc.document.document_type),
        source_class=source_class(doc.document.document_type),
        freshness=doc.knowledge.freshness,
        confidence=doc.knowledge.confidence,
        date=doc.document.date,
    )


def _conflicts_with_query(query: str, doc: KipDocument) -> bool:
    q = query.lower()
    if "bull" in q and doc.research.bear_case and not doc.research.bull_case:
        return True
    if "bear" in q and doc.research.bull_case and not doc.research.bear_case:
        return True
    return False


def _is_junk_document(doc: KipDocument) -> bool:
    title = (doc.document.title or "").strip()
    title_l = title.lower()
    if not title_l or title_l in _JUNK_TITLES:
        return True
    if _JUNK_TITLE_RE.match(title_l):
        return True
    content = (doc.cleaned_content or doc.content or "").strip()
    if len(content) < 60 and any(x in title_l for x in ("test", "hello", "sample", "demo")):
        return True
    return False
