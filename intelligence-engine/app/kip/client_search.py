"""Client / homepage search — NEVER answers directly; evidence-only pipeline (KIP P1)."""

from __future__ import annotations

import re
from typing import Any

from app.kip.extractors import KNOWN_TICKERS, TICKER_STOPWORDS
from app.kip.house_view import build_house_view, build_sector_house_view
from app.kip.models import (
    ClientSearchRequest,
    ClientSearchResponse,
    KipDocument,
    PredictionRecord,
)
from app.kip.rag import build_priority_evidence_pack


_TICKER_RE = re.compile(r"\b([A-Z]{2,12})(?:\.(?:NS|BO))?\b")

# Sector / theme aliases for questions that are not single-ticker.
_SECTOR_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    (
        "INDIA_IT",
        (
            "indian it",
            "india it",
            "it services",
            "it sector",
            "software services",
            "infosys",
            "tcs",
            "wipro",
            "hcltech",
            "tech mahindra",
        ),
    ),
    (
        "INDIA_BANKS",
        ("indian bank", "india bank", "private bank", "banking sector", "nbfc"),
    ),
]


def detect_intent(question: str) -> str:
    q = (question or "").lower()
    if any(w in q for w in ("compare", "vs", "versus", "relative")):
        return "comparison"
    if any(w in q for w in ("risk", "downside", "bear")):
        return "risk_assessment"
    if any(w in q for w in ("catalyst", "what next", "upcoming")):
        return "catalyst_watch"
    if any(w in q for w in ("valuation", "target", "fair value", "multiple")):
        return "valuation"
    if any(w in q for w in ("house view", "agi view", "your view", "stance")):
        return "house_view"
    if any(w in q for w in ("news", "latest", "today")):
        return "latest_developments"
    if any(w in q for w in ("buy", "sell", "hold", "should i")):
        return "recommendation_request"
    return "general_research"


def client_search(
    req: ClientSearchRequest,
    *,
    documents: dict[str, KipDocument],
    chunks: list,
    predictions: list[PredictionRecord] | None = None,
    dim: int = 256,
) -> ClientSearchResponse:
    intent = detect_intent(req.question)
    ticker = req.ticker or _infer_ticker(req.question, documents)
    if ticker and (ticker in TICKER_STOPWORDS or ticker not in KNOWN_TICKERS and not ticker.endswith("BANK")):
        # Reject noisy client/inferred tokens that are not real tickers.
        if ticker not in {t.upper() for d in documents.values() for t in d.investment.tickers}:
            ticker = None
    sector_key = None if ticker else _infer_sector(req.question, documents)
    pack = build_priority_evidence_pack(
        req.question,
        documents=documents,
        chunks=chunks,
        ticker=ticker,
        engine_states=req.engine_states,
        l4_opinion=req.l4_opinion,
        portfolio_exposure=req.portfolio_exposure,
        dim=dim,
    )
    house = None
    if ticker:
        company_docs = [
            d
            for d in documents.values()
            if ticker.upper() in {x.upper() for x in d.investment.tickers}
        ]
        house = build_house_view(ticker, company_docs, predictions=predictions or [])
    elif sector_key:
        sector_docs = _sector_documents(sector_key, documents, pack.documents_retrieved)
        house = build_sector_house_view(sector_key, sector_docs, predictions=predictions or [])

    validation = {
        "retrieved_agi_articles": pack.agi_research_used,
        "retrieved_broker_reports": pack.broker_reports_used,
        "retrieved_news": pack.news_used,
        "retrieved_filings": pack.filings_used,
        "engine_evidence": pack.engine_evidence,
        "l4_opinion": pack.l4_opinion,
        "knowledge_version": pack.knowledge_version,
        "confidence": pack.confidence_score,
        "freshness": pack.freshness_score,
        "last_updated": pack.last_updated.isoformat() if pack.last_updated else None,
        "conflicting_opinions": len(pack.conflicting_opinions),
        "intent": intent,
        "sector_key": sector_key,
        "answer_policy": "never_answer_directly",
    }
    return ClientSearchResponse(
        question=req.question,
        intent=intent,
        answer_policy="never_answer_directly",
        evidence=pack,
        house_view=house,
        validation=validation,
    )


def research_continuity_context(
    *,
    ticker: str | None,
    query: str,
    documents: dict[str, KipDocument],
    chunks: list,
    engine_states: list[dict[str, Any]] | None = None,
    l4_opinion: dict[str, Any] | None = None,
    portfolio_exposure: dict[str, Any] | None = None,
    dim: int = 256,
) -> dict[str, Any]:
    """Continuity pack for Research Writer — prior AGI + broker + engines + L4 + portfolio."""
    pack = build_priority_evidence_pack(
        query,
        documents=documents,
        chunks=chunks,
        ticker=ticker,
        engine_states=engine_states or [],
        l4_opinion=l4_opinion,
        portfolio_exposure=portfolio_exposure,
        dim=dim,
    )
    house = None
    if ticker:
        company_docs = [
            d
            for d in documents.values()
            if ticker.upper() in {x.upper() for x in d.investment.tickers}
        ]
        house = build_house_view(ticker, company_docs)

    changes = []
    if house:
        changes.extend(house.what_changed)
        if house.failed_assumptions:
            changes.append("Failed/retired assumptions present in history")
        if house.catalysts_occurred:
            changes.append(f"Catalysts occurred: {', '.join(house.catalysts_occurred[:5])}")

    academy_books: dict[str, Any] = {}
    try:
        from academy.books.production import research_writer_slice

        academy_books = research_writer_slice(query or "", ticker=ticker)
        try:
            from company_monitor.production import research_writer_slice as cms_research_writer_slice

            cms_slice = cms_research_writer_slice(query or "", ticker=ticker) or {}
            if isinstance(academy_books, dict) and cms_slice.get("enabled"):
                academy_books = {
                    **academy_books,
                    "company_monitor": cms_slice,
                    "what_changed": cms_slice.get("what_changed"),
                    "historical_timeline": cms_slice.get("historical_timeline"),
                    "financial_changes": cms_slice.get("financial_changes"),
                    "management_changes": cms_slice.get("management_changes"),
                    "valuation_changes": cms_slice.get("valuation_changes"),
                }
        except Exception:
            pass
    except Exception:
        academy_books = {}

    return {
        "documents_retrieved": pack.documents_retrieved,
        "knowledge_version": pack.knowledge_version,
        "source_list": pack.source_list,
        "agi_research_used": pack.agi_research_used,
        "broker_reports_used": pack.broker_reports_used,
        "news_used": pack.news_used,
        "filings_used": pack.filings_used,
        "engine_evidence": pack.engine_evidence,
        "l4_opinion": pack.l4_opinion,
        "portfolio_exposure": pack.portfolio_exposure,
        "conflicting_evidence": [c.model_dump(mode="json") for c in pack.conflicting_opinions],
        "freshness_score": pack.freshness_score,
        "confidence_score": pack.confidence_score,
        "last_updated": pack.last_updated.isoformat() if pack.last_updated else None,
        "house_view": house.model_dump(mode="json") if house else None,
        "what_changed_since_last_report": changes,
        "new_risks": (house.failed_assumptions if house else [])[:10],
        "new_catalysts": (house.catalysts_occurred if house else [])[:10],
        "retrieval_order": pack.retrieval_order,
        "answer_policy": "house_view_first_then_external",
        "academy_books": academy_books,
        "research_policy": {
            "use_academy_frameworks": True,
            "never_copy_book_text": True,
            "original_analysis_only": True,
        },
    }


def _infer_ticker(question: str, documents: dict[str, KipDocument]) -> str | None:
    known = set()
    for d in documents.values():
        known.update(t.upper() for t in d.investment.tickers)
    known |= KNOWN_TICKERS
    for m in _TICKER_RE.finditer(question or ""):
        tok = m.group(1).upper()
        if tok in TICKER_STOPWORDS:
            continue
        if tok in known:
            return tok
    # fallback: name mention in titles / known names
    q = (question or "").lower()
    name_map = {
        "infosys": "INFY",
        "tcs": "TCS",
        "wipro": "WIPRO",
        "hcl": "HCLTECH",
        "tech mahindra": "TECHM",
        "reliance": "RELIANCE",
        "icici": "ICICIBANK",
        "hdfc bank": "HDFCBANK",
        "idbi": "IDBI",
        "idbi bank": "IDBI",
        "idbi bank ltd": "IDBI",
        "idbi bank limited": "IDBI",
    }
    for name, ticker in name_map.items():
        if name in q and ticker in known:
            return ticker
    for d in documents.values():
        for t in d.investment.tickers:
            if t.lower() in q and t.upper() not in TICKER_STOPWORDS:
                return t.upper()
    return None


def _infer_sector(question: str, documents: dict[str, KipDocument]) -> str | None:
    q = (question or "").lower()
    for key, aliases in _SECTOR_ALIASES:
        if any(a in q for a in aliases):
            return key
    # Fallback: if retrieved corpus is dominated by one sector label
    counts: dict[str, int] = {}
    for d in documents.values():
        for s in d.investment.sectors or []:
            counts[str(s)] = counts.get(str(s), 0) + 1
    if not counts:
        return None
    top_sector, n = max(counts.items(), key=lambda kv: kv[1])
    if n >= 1 and any(tok in q for tok in ("sector", "services", "industry", "how is", "doing")):
        slug = re.sub(r"[^A-Za-z0-9]+", "_", top_sector).strip("_").upper()
        return slug[:32] or None
    return None


def _sector_documents(
    sector_key: str,
    documents: dict[str, KipDocument],
    retrieved_ids: list[str],
) -> list[KipDocument]:
    aliases = {
        "INDIA_IT": (
            "information technology",
            "it services",
            "indian it",
            "india it",
            "software",
            "tcs",
            "infy",
            "wipro",
        ),
        "INDIA_BANKS": ("financials", "bank", "nbfc", "credit"),
    }
    needles = aliases.get(sector_key, (sector_key.replace("_", " ").lower(),))
    out: list[KipDocument] = []
    seen: set[str] = set()
    # Prefer documents that RAG already retrieved for this question.
    for doc_id in retrieved_ids:
        d = documents.get(doc_id)
        if d is None or d.document_id in seen:
            continue
        blob = " ".join(
            [
                d.document.title or "",
                " ".join(d.investment.sectors or []),
                " ".join(d.investment.industries or []),
                (d.research.investment_thesis or "")[:400],
                (d.cleaned_content or "")[:800],
            ]
        ).lower()
        if any(n in blob for n in needles):
            out.append(d)
            seen.add(d.document_id)
    if out:
        return out
    for d in documents.values():
        blob = " ".join(
            [
                d.document.title or "",
                " ".join(d.investment.sectors or []),
                (d.research.investment_thesis or "")[:400],
            ]
        ).lower()
        if any(n in blob for n in needles):
            out.append(d)
    return out
