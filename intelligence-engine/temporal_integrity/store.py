"""In-memory TIRC telemetry store (process-local)."""

from __future__ import annotations

from threading import Lock
from typing import Any

_LOCK = Lock()
_REPORTS: list[dict[str, Any]] = []
_REJECTED: list[dict[str, Any]] = []
_LATEST_CERT: dict[str, Any] | None = None
_MAX = 200


def record_guard(report: dict[str, Any], rejected: list[dict[str, Any]] | None = None) -> None:
    with _LOCK:
        _REPORTS.insert(0, dict(report))
        del _REPORTS[_MAX:]
        for r in rejected or []:
            _REJECTED.insert(0, r)
        del _REJECTED[_MAX:]


def record_certification(cert: dict[str, Any]) -> None:
    global _LATEST_CERT
    with _LOCK:
        _LATEST_CERT = dict(cert)


def latest_reports(*, limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_REPORTS[: max(1, min(int(limit), _MAX))])


def latest_rejected(*, limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_REJECTED[: max(1, min(int(limit), _MAX))])


def latest_certification() -> dict[str, Any] | None:
    with _LOCK:
        return dict(_LATEST_CERT) if _LATEST_CERT else None
