"""IERE production facade."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.dashboard import evidence_dashboard
from evidence_retrieval.pipeline import retrieve_evidence
from evidence_retrieval.replay import replay_evidence, replay_pack
from evidence_retrieval.schema import FREEZE_LOCKS, IERE_VERSION, MODULE_CODE, PROGRAMME
from evidence_retrieval.store import get_graph, get_pack, last_run

__all__ = [
    "health",
    "dashboard",
    "search",
    "company",
    "document",
    "graph",
    "replay",
    "pack",
]


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IERE_VERSION,
        "deterministic_ranking": True,
        "never_raw_api": True,
        "never_pdf_to_reasoning": True,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return evidence_dashboard()


def search(
    question: str,
    *,
    ticker: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    return retrieve_evidence(question, ticker_hint=ticker, as_of=as_of)


def company(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    t = str(ticker or "").upper()
    return retrieve_evidence(
        f"What institutional evidence is available for {t}?",
        ticker_hint=t,
        as_of=as_of,
    )


def document(doc_id: str) -> dict[str, Any]:
    # Retrieve via IDI-backed discovery constrained to document id in ranked citations
    out = retrieve_evidence(f"document {doc_id}")
    items = [r for r in (out.get("ranked") or []) if r.get("document_id") == doc_id]
    return {
        "document_id": doc_id,
        "items": items,
        "n": len(items),
        "retrieval_id": out.get("retrieval_id"),
        "fabricated": False,
    }


def graph(graph_id: str | None = None) -> dict[str, Any]:
    if graph_id:
        g = get_graph(graph_id)
        return g or {"ok": False, "error": "not_found"}
    last = last_run() or {}
    gid = last.get("graph_id")
    return get_graph(gid) if gid else {"ok": False, "error": "no_graph"}


def replay(*, question: str, as_of: str, ticker: str | None = None) -> dict[str, Any]:
    return replay_evidence(question=question, as_of=as_of, ticker_hint=ticker)


def pack(pack_id: str) -> dict[str, Any]:
    return replay_pack(pack_id) or {"ok": False, "error": "not_found"}
