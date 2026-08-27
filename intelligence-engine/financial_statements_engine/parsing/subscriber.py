"""Subscribe to Evidence Event Bus — collectors never call parsers inline."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import subscribe
from financial_statements_engine.parsing.pipeline import parse_document
from financial_statements_engine.raw_evidence import read_raw_bytes


_BOUND = False


def on_evidence_stored(event: dict[str, Any]) -> None:
    payload = event.get("payload") or {}
    ticker = str(payload.get("ticker") or "").upper().strip()
    evidence_id = str(payload.get("evidence_id") or "")
    if not ticker or not evidence_id:
        return
    data = read_raw_bytes(ticker, evidence_id)
    if data is None:
        return
    meta = {
        "source": payload.get("source"),
        "period_end": payload.get("period_end"),
        "document_type": "xbrl",
    }
    # Soft parse — failures must not raise into the bus
    try:
        parse_document(ticker=ticker, data=data, evidence_id=evidence_id, meta=meta)
    except Exception:
        return


def bind_evidence_subscriber(*, subscriber_id: str = "fse04_pne") -> None:
    global _BOUND
    if _BOUND:
        return
    subscribe("evidence.stored", on_evidence_stored, subscriber_id=subscriber_id)
    _BOUND = True
