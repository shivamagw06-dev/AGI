"""In-memory IMEI store — immutable expectations, surprises, narratives."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_EXPECTATIONS: dict[str, dict[str, Any]] = {}
_SURPRISES: dict[str, dict[str, Any]] = {}
_NARRATIVES: dict[str, dict[str, Any]] = {}
_REVISIONS: list[dict[str, Any]] = []
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _EXPECTATIONS.clear()
        _SURPRISES.clear()
        _NARRATIVES.clear()
        _REVISIONS.clear()
        _RUNS.clear()


def put_expectation(obj: dict[str, Any]) -> dict[str, Any]:
    eid = str(obj.get("expectation_id") or "")
    if not eid:
        raise ValueError("expectation requires expectation_id")
    with _LOCK:
        if eid in _EXPECTATIONS:
            return deepcopy(_EXPECTATIONS[eid])
        _EXPECTATIONS[eid] = deepcopy(obj)
        return deepcopy(_EXPECTATIONS[eid])


def get_expectation(expectation_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _EXPECTATIONS.get(str(expectation_id or ""))
        return deepcopy(row) if row else None


def list_expectations(
    *,
    entity: str | None = None,
    metric: str | None = None,
    as_of: str | None = None,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_EXPECTATIONS.values())
    if entity:
        e = entity.upper()
        rows = [r for r in rows if str(r.get("entity") or "").upper() == e]
    if metric:
        m = metric.lower()
        rows = [r for r in rows if str(r.get("metric") or "").lower() == m]
    if kind:
        k = kind.lower()
        rows = [r for r in rows if str(r.get("kind") or "").lower() == k]
    if as_of:
        rows = [r for r in rows if str(r.get("available_from") or "") <= as_of]
    return [
        deepcopy(r)
        for r in sorted(
            rows,
            key=lambda x: (x.get("entity") or "", x.get("period") or "", x.get("available_from") or ""),
        )
    ]


def expectation_count() -> int:
    with _LOCK:
        return len(_EXPECTATIONS)


def put_surprise(obj: dict[str, Any]) -> dict[str, Any]:
    sid = str(obj.get("surprise_id") or "")
    if not sid:
        raise ValueError("surprise requires surprise_id")
    with _LOCK:
        if sid not in _SURPRISES:
            _SURPRISES[sid] = deepcopy(obj)
        return deepcopy(_SURPRISES[sid])


def list_surprises(*, entity: str | None = None, as_of: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_SURPRISES.values())
    if entity:
        e = entity.upper()
        rows = [r for r in rows if str(r.get("entity") or "").upper() == e]
    if as_of:
        rows = [r for r in rows if str(r.get("available_from") or "") <= as_of]
    return [deepcopy(r) for r in sorted(rows, key=lambda x: x.get("surprise_id") or "")]


def put_narrative(obj: dict[str, Any]) -> dict[str, Any]:
    nid = str(obj.get("narrative_id") or "")
    if not nid:
        raise ValueError("narrative requires narrative_id")
    with _LOCK:
        if nid not in _NARRATIVES:
            _NARRATIVES[nid] = deepcopy(obj)
        return deepcopy(_NARRATIVES[nid])


def list_narratives() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_NARRATIVES.items())]


def get_narrative(narrative_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _NARRATIVES.get(str(narrative_id or "").lower())
        return deepcopy(row) if row else None


def put_revision(obj: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        _REVISIONS.append(deepcopy(obj))
        return deepcopy(obj)


def list_revisions(*, entity: str | None = None, as_of: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_REVISIONS)
    if entity:
        e = entity.upper()
        rows = [r for r in rows if str(r.get("entity") or "").upper() == e]
    if as_of:
        rows = [r for r in rows if str(r.get("available_from") or "") <= as_of]
    return [deepcopy(r) for r in sorted(rows, key=lambda x: x.get("available_from") or "")]


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
