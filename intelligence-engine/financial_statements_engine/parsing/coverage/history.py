"""Permanent coverage history — never rewritten."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def _history_dir(ticker: str):
    p = ensure_dirs() / "parsing" / "coverage" / "history" / ticker.upper().strip()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _history_path(ticker: str, document_hash: str):
    return _history_dir(ticker) / f"{document_hash[:32]}.jsonl"


def append_history(
    *,
    ticker: str,
    document_hash: str,
    matrix: dict[str, Any],
    scorecard: dict[str, Any],
) -> dict[str, Any]:
    entry = {
        "recorded_at": now_iso(),
        "matrix_id": matrix.get("matrix_id"),
        "manifest_id": matrix.get("manifest_id"),
        "draft_id": matrix.get("draft_id"),
        "document_hash": document_hash,
        "ticker": ticker.upper().strip(),
        "parser_name": matrix.get("parser_name"),
        "parser_version": matrix.get("parser_version"),
        "pne_version": matrix.get("pne_version"),
        "coverage_percentage": scorecard.get("coverage_percentage"),
        "coverage_fingerprint": matrix.get("coverage_fingerprint"),
        "unknown_label_count": scorecard.get("unknown_label_count"),
        "unsupported_section_count": scorecard.get("unsupported_section_count"),
        "core_coverage": scorecard.get("core_coverage"),
        "status_counts": scorecard.get("status_counts"),
    }
    path = _history_path(ticker, document_hash)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
    # Also mirror index by matrix id for lookup
    idx = ensure_dirs() / "parsing" / "coverage" / "history_index" / f"{matrix['matrix_id'].replace(':', '_')}.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(idx, entry)
    publish(
        "coverage.history.appended.v1",
        {
            "ticker": ticker,
            "document_hash": document_hash,
            "matrix_id": matrix.get("matrix_id"),
            "coverage_percentage": scorecard.get("coverage_percentage"),
            "parser_version": matrix.get("parser_version"),
        },
    )
    return entry


def list_history(ticker: str, document_hash: str | None = None) -> list[dict[str, Any]]:
    t = ticker.upper().strip()
    root = _history_dir(t)
    paths = []
    if document_hash:
        p = _history_path(t, document_hash)
        if p.exists():
            paths = [p]
    else:
        paths = sorted(root.glob("*.jsonl"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def latest_for_document(ticker: str, document_hash: str) -> dict[str, Any] | None:
    rows = list_history(ticker, document_hash)
    return rows[-1] if rows else None


def prior_for_document(ticker: str, document_hash: str) -> dict[str, Any] | None:
    rows = list_history(ticker, document_hash)
    if len(rows) < 2:
        return None
    return rows[-2]
