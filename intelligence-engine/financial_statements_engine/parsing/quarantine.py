"""Quarantine unsupported / failed documents for review."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def quarantine_document(
    *,
    ticker: str,
    evidence_id: str,
    reason: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = ensure_dirs()
    path = root / "parsing" / "quarantine" / ticker.upper().strip() / f"{evidence_id.replace(':', '_')}.json"
    record = {
        "ticker": ticker.upper().strip(),
        "evidence_id": evidence_id,
        "reason": reason,
        "detail": detail or {},
        "quarantined_at": now_iso(),
        "layer": "quarantine",
    }
    write_json_atomic(path, record)
    return {**record, "path": str(path)}
