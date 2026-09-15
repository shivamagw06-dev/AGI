"""Discovery Collector — detects filings; never downloads (FSE-02 §6.1)."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.collection.jobs import new_uuid
from financial_statements_engine.collection.metadata import extract_filing_metadata
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def persist_discovery(ticker: str, row: dict[str, Any]) -> dict[str, Any]:
    meta = extract_filing_metadata(row)
    discovery_id = str(row.get("discovery_id") or new_uuid())
    record = {
        "discovery_id": discovery_id,
        "ticker": (meta.get("ticker") or ticker).upper().strip(),
        "discovered_at": now_iso(),
        "metadata": meta,
        "raw_row": {k: v for k, v in row.items() if k not in ("income_statement", "balance_sheet", "cash_flow")},
    }
    root = ensure_dirs()
    path = root / "collection" / "discovery" / record["ticker"] / f"{discovery_id}.json"
    write_json_atomic(path, record)
    return record


def emit_discovery(record: dict[str, Any], *, updated: bool = False) -> dict[str, Any]:
    event_type = "discovery.filing_updated" if updated else "discovery.filing_found"
    return publish(
        event_type,
        {
            "discovery_id": record.get("discovery_id"),
            "ticker": record.get("ticker"),
            "metadata": record.get("metadata"),
        },
    )


def discover_from_rows(ticker: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist + emit discovery events for adapter rows."""
    out: list[dict[str, Any]] = []
    for row in rows:
        record = persist_discovery(ticker, row)
        event = emit_discovery(record, updated=bool(row.get("updated")))
        out.append({"discovery": record, "event": event})
    return out


def load_discoveries(ticker: str) -> list[dict[str, Any]]:
    root = ensure_dirs()
    d = root / "collection" / "discovery" / ticker.upper().strip()
    if not d.exists():
        return []
    rows = []
    for path in sorted(d.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows
