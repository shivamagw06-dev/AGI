"""Append-only decision audit trail — reproducible institutional judgements."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

_AUDIT: dict[str, dict[str, Any]] = {}
_MONITORING: dict[str, list[dict[str, Any]]] = {}


def store_audit(record: dict[str, Any]) -> dict[str, Any]:
    row = deepcopy(record)
    aid = str(row.get("audit_id") or uuid4())
    row["audit_id"] = aid
    row["append_only"] = True
    row["overwritten"] = False
    _AUDIT[aid] = row
    ticker = str(row.get("ticker") or "").upper()
    if ticker:
        _MONITORING.setdefault(ticker, []).append(
            {
                "audit_id": aid,
                "ticker": ticker,
                "monitoring": row.get("monitoring"),
                "recommendation_status": (row.get("recommendation_gate") or {}).get("status"),
            }
        )
    return deepcopy(row)


def get_audit(audit_id: str) -> dict[str, Any] | None:
    row = _AUDIT.get(str(audit_id))
    return deepcopy(row) if row else None


def list_audits(*, limit: int = 50) -> list[dict[str, Any]]:
    rows = list(_AUDIT.values())[-max(1, min(limit, 200)) :]
    return deepcopy(rows)


def monitoring_for(ticker: str) -> list[dict[str, Any]]:
    return deepcopy(_MONITORING.get((ticker or "").upper(), []))


def clear_for_tests() -> None:
    _AUDIT.clear()
    _MONITORING.clear()
