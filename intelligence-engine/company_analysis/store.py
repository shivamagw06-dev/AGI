"""In-memory analysis report store (process-local; soft layer)."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any


_LOCK = Lock()
_REPORTS: dict[str, dict[str, Any]] = {}
_HISTORY: list[dict[str, Any]] = []


def put_report(ticker: str, report: dict[str, Any]) -> dict[str, Any]:
    t = (ticker or "").upper()
    with _LOCK:
        _REPORTS[t] = deepcopy(report)
        _HISTORY.append({"ticker": t, "at": report.get("generated_at"), "readiness": (report.get("recommendation_readiness") or {}).get("overall")})
        if len(_HISTORY) > 200:
            del _HISTORY[:-200]
    return report


def get_report(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper()
    with _LOCK:
        row = _REPORTS.get(t)
        return deepcopy(row) if row else None


def list_reports(limit: int = 30) -> list[dict[str, Any]]:
    with _LOCK:
        items = list(_REPORTS.values())
    items.sort(key=lambda r: str(r.get("generated_at") or ""), reverse=True)
    return [deepcopy(x) for x in items[:limit]]


def metrics() -> dict[str, Any]:
    with _LOCK:
        n = len(_REPORTS)
        overalls = [
            float(((r.get("recommendation_readiness") or {}).get("overall") or 0))
            for r in _REPORTS.values()
        ]
        eligible = sum(
            1
            for r in _REPORTS.values()
            if ((r.get("recommendation_readiness") or {}).get("gate") or "") == "Eligible"
        )
    avg = round(sum(overalls) / len(overalls), 1) if overalls else 0.0
    return {
        "reports": n,
        "avg_readiness": avg,
        "eligible_count": eligible,
        "history_events": len(_HISTORY),
    }


def reset_for_tests() -> None:
    with _LOCK:
        _REPORTS.clear()
        _HISTORY.clear()
