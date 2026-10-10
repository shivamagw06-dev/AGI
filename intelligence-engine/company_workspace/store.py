"""Process-local Company Workspace cache + Mission Control metrics."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
# ticker → last assembled workspace (OfficeResponse payload)
_WORKSPACES: dict[str, dict[str, Any]] = {}
# ticker → module pass-through cache (FIRE/IO boards; never rescored here)
_MODULE_CACHE: dict[str, dict[str, dict[str, Any]]] = {}
# ticker → research references (from IO / PEB; presentation only)
_RESEARCH: dict[str, list[dict[str, Any]]] = {}
# ticker → timeline events
_TIMELINE: dict[str, list[dict[str, Any]]] = {}
_VIEWED: list[str] = []
_METRICS: dict[str, Any] = {
    "companies_viewed": 0,
    "workspace_refreshes": 0,
    "assemblies": 0,
    "event_refreshes": 0,
    "coverage_hits": 0,
    "coverage_misses": 0,
    "evidence_blocks_total": 0,
    "last_ticker": None,
}
_VIEWED_LIMIT = 50
_TIMELINE_LIMIT = 200
_RESEARCH_LIMIT = 50


def _now() -> str:
    try:
        from financial_statements_engine.util import now_iso

        return now_iso()
    except Exception:  # noqa: BLE001
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def put_workspace(ticker: str, workspace: dict[str, Any]) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    if not t:
        raise ValueError("ticker required")
    with _LOCK:
        _WORKSPACES[t] = deepcopy(workspace)
        _METRICS["assemblies"] = int(_METRICS["assemblies"]) + 1
        _METRICS["last_ticker"] = t
        if t not in _VIEWED:
            _VIEWED.append(t)
            _METRICS["companies_viewed"] = len(_VIEWED)
        else:
            _VIEWED.remove(t)
            _VIEWED.append(t)
        if len(_VIEWED) > _VIEWED_LIMIT:
            del _VIEWED[: len(_VIEWED) - _VIEWED_LIMIT]
            _METRICS["companies_viewed"] = len(_VIEWED)
    return get_workspace(t)  # type: ignore[return-value]


def get_workspace(ticker: str) -> Optional[dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    with _LOCK:
        w = _WORKSPACES.get(t)
        return deepcopy(w) if w else None


def put_module_cache(ticker: str, modules: dict[str, dict[str, Any]]) -> None:
    t = str(ticker or "").strip().upper()
    if not t:
        return
    with _LOCK:
        cur = _MODULE_CACHE.setdefault(t, {})
        for k, v in (modules or {}).items():
            if isinstance(v, dict):
                cur[str(k)] = deepcopy(v)


def get_module_cache(ticker: str) -> dict[str, dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    with _LOCK:
        return deepcopy(_MODULE_CACHE.get(t) or {})


def record_research(ticker: str, ref: dict[str, Any]) -> None:
    t = str(ticker or "").strip().upper()
    if not t:
        return
    row = {**deepcopy(ref), "recorded_at": ref.get("recorded_at") or _now()}
    with _LOCK:
        rows = _RESEARCH.setdefault(t, [])
        rows.append(row)
        if len(rows) > _RESEARCH_LIMIT:
            del rows[: len(rows) - _RESEARCH_LIMIT]


def list_research(ticker: str) -> list[dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    with _LOCK:
        return deepcopy(_RESEARCH.get(t) or [])


def append_timeline(ticker: str, event: dict[str, Any]) -> None:
    t = str(ticker or "").strip().upper()
    if not t:
        return
    row = {
        "at": event.get("at") or event.get("ts") or _now(),
        "event_type": event.get("event_type") or event.get("type") or "unknown",
        "source": event.get("source") or event.get("producer") or "cw-01",
        "summary": event.get("summary") or "",
        "payload": deepcopy(event.get("payload") or {}),
    }
    with _LOCK:
        rows = _TIMELINE.setdefault(t, [])
        rows.append(row)
        rows.sort(key=lambda r: str(r.get("at") or ""))
        if len(rows) > _TIMELINE_LIMIT:
            del rows[: len(rows) - _TIMELINE_LIMIT]


def list_timeline(ticker: str, *, limit: int = 100) -> list[dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    with _LOCK:
        rows = list(_TIMELINE.get(t) or [])
    if limit and len(rows) > int(limit):
        return deepcopy(rows[-int(limit) :])
    return deepcopy(rows)


def mark_refresh(ticker: str, *, reason: str = "event") -> None:
    t = str(ticker or "").strip().upper()
    with _LOCK:
        _METRICS["workspace_refreshes"] = int(_METRICS["workspace_refreshes"]) + 1
        _METRICS["event_refreshes"] = int(_METRICS["event_refreshes"]) + 1
        # Drop assembled workspace so next GET reassembles from caches
        if t in _WORKSPACES:
            del _WORKSPACES[t]
    append_timeline(
        t,
        {
            "event_type": "workspace.refresh",
            "source": "cw-01",
            "summary": f"Workspace marked stale ({reason})",
            "payload": {"reason": reason},
        },
    )


def record_coverage(*, hit: bool, evidence_blocks: int = 0) -> None:
    with _LOCK:
        if hit:
            _METRICS["coverage_hits"] = int(_METRICS["coverage_hits"]) + 1
        else:
            _METRICS["coverage_misses"] = int(_METRICS["coverage_misses"]) + 1
        _METRICS["evidence_blocks_total"] = int(_METRICS["evidence_blocks_total"]) + int(evidence_blocks or 0)


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
        viewed = list(_VIEWED)
        hits = int(m.get("coverage_hits") or 0)
        misses = int(m.get("coverage_misses") or 0)
        total = hits + misses
    completeness = round(hits / total, 4) if total else 0.0
    return {
        **m,
        "viewed_tickers": viewed[-20:],
        "panels": {
            "companies_viewed": m.get("companies_viewed"),
            "workspace_refreshes": m.get("workspace_refreshes"),
            "coverage": {
                "hits": hits,
                "misses": misses,
                "ratio": completeness,
            },
            "evidence_completeness": completeness,
        },
    }


def reset_for_tests() -> None:
    global _WORKSPACES, _MODULE_CACHE, _RESEARCH, _TIMELINE, _VIEWED
    with _LOCK:
        _WORKSPACES = {}
        _MODULE_CACHE = {}
        _RESEARCH = {}
        _TIMELINE = {}
        _VIEWED = []
        for k in list(_METRICS.keys()):
            if k in {"last_ticker"}:
                _METRICS[k] = None
            else:
                _METRICS[k] = 0
