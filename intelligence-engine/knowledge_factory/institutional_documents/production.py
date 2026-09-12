"""IDI production facade — APIs / Mission Control / soft scheduler entry."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.dashboards import documents_dashboard
from knowledge_factory.institutional_documents.pipeline import run_institutional_documents_pipeline
from knowledge_factory.institutional_documents.replay import replay_as_of, replay_document
from knowledge_factory.institutional_documents.schema import FREEZE_LOCKS, IDI_VERSION, LAYER, PROGRAMME
from knowledge_factory.institutional_documents.timeline import company_document_timeline


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IDI_VERSION,
        "architecture_status": "INSTITUTIONAL_DOCUMENTS_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "not_summarisation": True,
        "not_recommendations": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/documents",
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return documents_dashboard()


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_institutional_documents_pipeline(**kwargs)


def company(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").upper()
    docs = store.list_documents(ticker=t)
    objects = store.list_objects(ticker=t)
    packs = store.list_packs(ticker=t)
    return {
        "company": t,
        "documents": docs,
        "objects": objects,
        "packs": packs,
        "timeline": company_document_timeline(t),
        "n_documents": len(docs),
        "fabricated": False,
        "recommendation": None,
    }


def report(doc_id: str) -> dict[str, Any]:
    doc = store.get_document(doc_id)
    if not doc:
        return {"ok": False, "error": "not_found", "document_id": doc_id}
    # Do not require returning full text in all surfaces; include for evidence use
    chunks = store.get_chunks(doc_id)
    return {
        "ok": True,
        "document": doc,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "replay": replay_document(doc_id),
        "fabricated": False,
        "recommendation": None,
    }


def search(
    *,
    q: str | None = None,
    ticker: str | None = None,
    doc_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    docs = store.list_documents(ticker=ticker, doc_type=doc_type)
    query = (q or "").strip().lower()
    hits = []
    if query:
        for d in docs:
            blob = f"{d.get('title')} {d.get('type')} {d.get('company')}".lower()
            # also search chunk text
            matched_chunks = []
            for c in store.get_chunks(str(d.get("document_id"))):
                if query in (c.get("text") or "").lower() or query in (c.get("heading") or "").lower():
                    matched_chunks.append(
                        {
                            "chunk_id": c.get("chunk_id"),
                            "section": c.get("section"),
                            "page": c.get("page"),
                            "heading": c.get("heading"),
                        }
                    )
            if query in blob or matched_chunks:
                hits.append(
                    {
                        "document_id": d.get("document_id"),
                        "company": d.get("company"),
                        "type": d.get("type"),
                        "title": d.get("title"),
                        "matched_chunks": matched_chunks[:10],
                    }
                )
    else:
        hits = [
            {
                "document_id": d.get("document_id"),
                "company": d.get("company"),
                "type": d.get("type"),
                "title": d.get("title"),
                "matched_chunks": [],
            }
            for d in docs
        ]
    return {"q": q, "n": len(hits[:limit]), "hits": hits[:limit], "fabricated": False}


def replay(*, as_of: str, ticker: str | None = None, document_id: str | None = None) -> dict[str, Any]:
    if document_id:
        return replay_document(document_id) or {"ok": False, "error": "not_found"}
    return replay_as_of(as_of, ticker=ticker)
