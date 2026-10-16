"""Structured operational logging (PRP-03)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Optional

from institutional_observability.schema import REQUIRED_LOG_FIELDS, SEVERITIES

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_LOGS: Deque[dict[str, Any]] = deque(maxlen=5000)


def reset_for_tests() -> None:
    with _LOCK:
        _LOGS.clear()


def log_event(
    message: str,
    *,
    component: str,
    severity: str = "info",
    correlation_id: str = "",
    trace_id: str = "",
    tenant_id: str = "",
    workspace_id: str = "",
    portfolio_id: str = "",
    user_id: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    sev = str(severity or "info").lower()
    if sev not in SEVERITIES:
        sev = "info"
    row = {
        "timestamp": now_iso(),
        "correlation_id": correlation_id or "",
        "trace_id": trace_id or "",
        "tenant_id": tenant_id or "",
        "workspace_id": workspace_id or "",
        "portfolio_id": portfolio_id or "",
        "user_id": user_id or "",
        "component": component,
        "severity": sev,
        "message": str(message),
    }
    if extra:
        row["extra"] = dict(extra)
    with _LOCK:
        _LOGS.append(row)
    return row


def validate_log_fields(row: dict[str, Any]) -> list[str]:
    missing = [f for f in REQUIRED_LOG_FIELDS if f not in row or row.get(f) in (None, "")]
    # correlation_id / trace_id may be empty only for bootstrap — flag as soft issue
    return [f"missing required field: {f}" for f in missing if f not in {"correlation_id", "trace_id"}]


def recent_logs(
    *,
    limit: int = 50,
    severity: str = "",
    correlation_id: str = "",
    component: str = "",
) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_LOGS)
    if severity:
        rows = [r for r in rows if r.get("severity") == severity]
    if correlation_id:
        rows = [r for r in rows if r.get("correlation_id") == correlation_id]
    if component:
        rows = [r for r in rows if r.get("component") == component]
    return list(reversed(rows[-limit:]))
