"""FSE-04 Parsing & Normalization — production façades."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.parsing.pipeline import parse_document
from financial_statements_engine.parsing.registry import registry_manifest
from financial_statements_engine.parsing.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    QUALITY_TARGETS,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VALIDATES_ACCOUNTING,
    VERSION,
    WORKSTREAM_ID,
    WRITES_WAREHOUSE,
)
from financial_statements_engine.parsing.subscriber import bind_evidence_subscriber
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    bind_evidence_subscriber()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "writes_warehouse": WRITES_WAREHOUSE,
        "validates_accounting": VALIDATES_ACCOUNTING,
        "parsers": registry_manifest(),
        "quality_targets": QUALITY_TARGETS,
        "event_bus": get_bus().stats(),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_04_PARSING_NORMALIZATION_ENGINE.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    root = ensure_dirs()
    drafts = root / "parsing" / "drafts"
    quarantine = root / "parsing" / "quarantine"
    draft_n = sum(1 for _ in drafts.rglob("*.json")) if drafts.exists() else 0
    q_n = sum(1 for _ in quarantine.rglob("*.json")) if quarantine.exists() else 0
    events = get_bus().tail(100)
    parse_events = [e for e in events if str(e.get("event_type", "")).startswith("parse.")]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "drafts": draft_n,
        "quarantine": q_n,
        "recent_parse_events": parse_events[-20:],
        "quality_targets": QUALITY_TARGETS,
        "writes_warehouse": False,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def parse_bytes(
    ticker: str,
    data: bytes,
    *,
    evidence_id: str | None = None,
    document_type: str = "xbrl",
    period_end: str | None = None,
    period_type: str | None = None,
    consolidation_type: str = "consolidated",
    source: str = "nse_xbrl",
) -> dict[str, Any]:
    eid = evidence_id or f"inline:{ticker.upper()}:{_short_hash(data)}"
    return parse_document(
        ticker=ticker,
        data=data,
        evidence_id=eid,
        meta={
            "document_type": document_type,
            "period_end": period_end,
            "period_type": period_type or ("annual" if period_end else None),
            "consolidation_type": consolidation_type,
            "source": source,
        },
    )


def parse_file(ticker: str, path: str, **kwargs: Any) -> dict[str, Any]:
    data = Path(path).read_bytes()
    return parse_bytes(ticker, data, **kwargs)


def _short_hash(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()[:16]
