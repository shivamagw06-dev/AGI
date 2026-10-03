"""Production Event Bus binding — auto-start workflows on evidence.stored.

Wired from app lifespan. Does not modify collectors or the parse subscriber.
Flow: evidence.stored → orchestrator → PARSE → VALIDATE → WAREHOUSE → DME.
"""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import subscribe
from financial_statements_engine.orchestrator.engine import create_workflow, run_workflow

_BOUND = False


def on_evidence_stored(event: dict[str, Any]) -> None:
    payload = event.get("payload") or {}
    try:
        created = create_workflow(
            {
                "ticker": payload.get("ticker"),
                "company_id": payload.get("company_id"),
                "period": payload.get("period_end") or payload.get("period"),
                "filing_type": payload.get("period_type") or payload.get("document_type") or "unknown",
                "document_hash": payload.get("content_sha256") or payload.get("document_hash"),
                "evidence_id": payload.get("evidence_id"),
                "document_type": payload.get("document_type"),
                "source": payload.get("source"),
            },
            auto_queue=True,
        )
        wid = (created.get("workflow") or {}).get("workflow_id")
        if wid and created.get("created"):
            run_workflow(str(wid))
    except Exception:
        return


def bind_orchestrator_subscriber(*, subscriber_id: str = "fse00_orchestrator") -> None:
    global _BOUND
    if _BOUND:
        return
    subscribe("evidence.stored", on_evidence_stored, subscriber_id=subscriber_id)
    _BOUND = True
