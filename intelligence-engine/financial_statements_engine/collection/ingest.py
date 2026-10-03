"""FSE-02.1 — Canonical ingestion façade.

Collectors become adapters that call ``ingest()``. This module owns:

* Raw Evidence Store write (idempotent)
* Exactly one ``evidence.stored`` emission per new filing
* Mission Control metrics
* Optional HD dual-write callback (temporary migration safety)

Collectors never call Parse. The orchestrator reacts to ``evidence.stored``.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.collection.flags import canonical_ingest_enabled, dual_write_hd_enabled
from financial_statements_engine.collection.ingest_metrics import record_ingest_metric
from financial_statements_engine.collection.schema import VERSION
from financial_statements_engine.collection.writer import write_evidence
from financial_statements_engine.observability import record_event

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "fse-02.1-v1.0.0"
HdCallback = Callable[[], dict[str, Any] | None]


def _evidence_payload(
    *,
    write_result: dict[str, Any],
    ticker: str,
    source: str,
    document_type: str,
    period_type: str | None,
    period_end: str | None,
    source_url: str | None,
    company_name: str | None,
    filing_type: str | None,
    collector: str | None,
) -> dict[str, Any]:
    meta = write_result.get("meta") or {}
    return {
        "evidence_id": write_result.get("evidence_id"),
        "ticker": ticker.upper().strip(),
        "company_id": ticker.upper().strip(),
        "company_name": company_name,
        "source": source,
        "source_url": source_url,
        "content_sha256": write_result.get("content_sha256"),
        "document_hash": write_result.get("content_sha256"),
        "document_type": document_type,
        "period_type": period_type,
        "period_end": period_end,
        "period": period_end,
        "filing_type": filing_type or period_type or document_type,
        "logical_key": write_result.get("logical_key"),
        "path": meta.get("bytes_path"),
        "collector": collector,
        "migration": MIGRATION_VERSION,
        "action": write_result.get("action"),
    }


def ingest(
    *,
    ticker: str,
    content: bytes,
    source: str,
    document_type: str = "xbrl",
    period_type: str | None = None,
    period_end: str | None = None,
    source_url: str | None = None,
    company_name: str | None = None,
    filing_type: str | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    entity: str | None = None,
    consolidation: str | None = None,
    emit_event: bool = True,
    collector: str | None = None,
    hd_callback: HdCallback | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical entry for every financial-statement filing.

    Returns a result dict with ``action`` in
    ``stored | duplicate_skipped | restatement_candidate | disabled | failed``.
    """
    t0 = time.perf_counter()
    t = (ticker or "").upper().strip()
    if not t:
        return {"ok": False, "action": "failed", "error": "ticker_required", "event_emitted": False}
    if content is None:
        return {"ok": False, "action": "failed", "error": "content_required", "event_emitted": False, "ticker": t}
    if isinstance(content, str):
        content = content.encode("utf-8")
    if not isinstance(content, (bytes, bytearray)):
        return {"ok": False, "action": "failed", "error": "content_must_be_bytes", "event_emitted": False, "ticker": t}

    if not canonical_ingest_enabled():
        hd: dict[str, Any] | None = None
        if dual_write_hd_enabled() and hd_callback is not None:
            try:
                hd = hd_callback() or {}
            except Exception as exc:  # noqa: BLE001
                hd = {"ok": False, "error": str(exc)[:160]}
        return {
            "ok": True,
            "action": "disabled",
            "ticker": t,
            "event_emitted": False,
            "dual_write_hd": hd,
            "migration": MIGRATION_VERSION,
            "collection_version": VERSION,
        }

    try:
        write_result = write_evidence(
            ticker=t,
            data=bytes(content),
            source=str(source or "unknown"),
            source_url=source_url,
            document_type=str(document_type or "unknown"),
            period_type=period_type,
            period_end=period_end,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            entity=entity or t,
            consolidation=consolidation,
            extra=provenance,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        record_ingest_metric(
            {
                "ticker": t,
                "source": source,
                "action": "failed",
                "event_emitted": False,
                "latency_ms": latency_ms,
                "collector": collector,
                "error": str(exc)[:160],
            }
        )
        return {
            "ok": False,
            "action": "failed",
            "ticker": t,
            "error": str(exc)[:160],
            "event_emitted": False,
            "latency_ms": latency_ms,
            "migration": MIGRATION_VERSION,
        }

    action = str(write_result.get("action") or "stored")
    event_emitted = False
    event: dict[str, Any] | None = None
    payload = _evidence_payload(
        write_result=write_result,
        ticker=t,
        source=str(source or "unknown"),
        document_type=str(document_type or "unknown"),
        period_type=period_type,
        period_end=period_end,
        source_url=source_url,
        company_name=company_name,
        filing_type=filing_type,
        collector=collector,
    )
    if provenance:
        # Additive provenance — never drop fields
        for k, v in provenance.items():
            if k not in payload or payload.get(k) in (None, ""):
                payload[k] = v
        payload["provenance"] = provenance

    if emit_event:
        if action == "duplicate_skipped":
            event = publish("evidence.duplicate_skipped", payload)
            logger.info(
                "fse02.1 duplicate filing detected ticker=%s evidence_id=%s logical_key=%s",
                t,
                write_result.get("evidence_id"),
                write_result.get("logical_key"),
            )
        else:
            # stored or restatement_candidate → exactly one evidence.stored
            event = publish("evidence.stored", payload)
            event_emitted = True
            if action == "restatement_candidate":
                publish(
                    "evidence.restatement_candidate",
                    {
                        **payload,
                        "prior_evidence_id": write_result.get("prior_evidence_id"),
                    },
                )

    hd_result: dict[str, Any] | None = None
    if dual_write_hd_enabled() and hd_callback is not None:
        try:
            hd_result = hd_callback() or {"ok": True}
        except Exception as exc:  # noqa: BLE001
            logger.warning("fse02.1 dual-write HD failed ticker=%s err=%s", t, exc)
            hd_result = {"ok": False, "error": str(exc)[:160]}

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    record_ingest_metric(
        {
            "ticker": t,
            "source": source,
            "document_type": document_type,
            "period_end": period_end,
            "period_type": period_type,
            "action": action,
            "event_emitted": event_emitted,
            "event_id": (event or {}).get("event_id"),
            "evidence_id": write_result.get("evidence_id"),
            "content_sha256": write_result.get("content_sha256"),
            "latency_ms": latency_ms,
            "collector": collector,
            "dual_write_hd": bool(hd_result is not None),
        }
    )
    record_event(
        {
            "stage": "canonical_ingest",
            "ticker": t,
            "action": action,
            "collector": collector,
            "migration": MIGRATION_VERSION,
        }
    )

    return {
        "ok": True,
        "action": action,
        "ticker": t,
        "evidence_id": write_result.get("evidence_id"),
        "content_sha256": write_result.get("content_sha256"),
        "logical_key": write_result.get("logical_key"),
        "write": write_result,
        "event_emitted": event_emitted,
        "event_id": (event or {}).get("event_id"),
        "event": event,
        "dual_write_hd": hd_result,
        "latency_ms": latency_ms,
        "migration": MIGRATION_VERSION,
        "collection_version": VERSION,
        "prior_evidence_id": write_result.get("prior_evidence_id"),
    }


def ingest_structured_json(
    *,
    ticker: str,
    payload: dict[str, Any] | list[Any],
    source: str,
    document_type: str = "structured_financials",
    period_type: str | None = None,
    period_end: str | None = None,
    source_url: str | None = None,
    collector: str | None = None,
    hd_callback: HdCallback | None = None,
    filing_type: str | None = None,
) -> dict[str, Any]:
    """Ingest structured collector output as raw JSON evidence (Yahoo / connector path)."""
    import json

    content = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return ingest(
        ticker=ticker,
        content=content,
        source=source,
        document_type=document_type,
        period_type=period_type,
        period_end=period_end,
        source_url=source_url,
        collector=collector,
        hd_callback=hd_callback,
        filing_type=filing_type or period_type or document_type,
    )
