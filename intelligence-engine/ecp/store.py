"""In-memory ECP completion reports."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ecp.schema import ECP_VERSION

_LOCK = threading.RLock()
_REPORTS: List[Dict[str, Any]] = []
_BY_TICKER: Dict[str, Dict[str, Any]] = {}
_MAX = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_report(report: Dict[str, Any]) -> Dict[str, Any]:
    row = {
        **report,
        "ecp_version": ECP_VERSION,
        "saved_at": _now(),
    }
    ticker = str(row.get("ticker") or "").upper()
    with _LOCK:
        _REPORTS.insert(0, row)
        del _REPORTS[_MAX:]
        if ticker:
            _BY_TICKER[ticker] = row
    return dict(row)


def get_report(ticker: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _BY_TICKER.get((ticker or "").upper())
        return dict(row) if row else None


def list_reports(*, limit: int = 40) -> List[Dict[str, Any]]:
    with _LOCK:
        return [dict(r) for r in _REPORTS[: max(1, min(int(limit), 200))]]


def reset_for_tests() -> None:
    with _LOCK:
        _REPORTS.clear()
        _BY_TICKER.clear()
