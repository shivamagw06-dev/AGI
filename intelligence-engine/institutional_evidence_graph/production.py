"""IEG production facade."""

from __future__ import annotations

from typing import Any

from institutional_evidence_graph.assembler.engine import build_evidence_graph
from institutional_evidence_graph.dashboard.board import evidence_graph_dashboard
from institutional_evidence_graph.schema import FREEZE_LOCKS, IEG_VERSION, PROGRAMME
from institutional_evidence_graph import store


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "ieg_version": IEG_VERSION,
        "soft_wire_only": True,
        "guides_evidence": True,
        "replaces_reasoning": False,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/institutional-evidence-graph",
        "fabricated": False,
    }


def build(**kwargs: Any) -> dict[str, Any]:
    out = build_evidence_graph(**kwargs)
    store.record(out)
    return out


def company(ticker: str, *, as_of: str | None = None, question: str | None = None) -> dict[str, Any]:
    return build(
        question=question or f"Evidence graph for {ticker}",
        entities=[{"type": "company", "id": ticker, "confidence": 0.99}],
        ticker_hint=ticker,
        as_of=as_of,
        concept_mode=False,
    )


def dashboard() -> dict[str, Any]:
    return evidence_graph_dashboard()


def history(*, limit: int = 50) -> dict[str, Any]:
    return {"n": min(limit, 500), "rows": store.list_rows(limit=limit), "fabricated": False}
