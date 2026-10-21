"""In-memory Government Intelligence store (soft, immutable policies)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_POLICIES: dict[str, dict[str, Any]] = {}
_BODIES: dict[str, dict[str, Any]] = {}
_TIMELINE: dict[str, Any] | None = None
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    global _TIMELINE
    with _LOCK:
        _POLICIES.clear()
        _BODIES.clear()
        _TIMELINE = None
        _RUNS.clear()


def put_body(body: dict[str, Any]) -> dict[str, Any]:
    bid = str(body.get("body_id") or "")
    if not bid:
        raise ValueError("body requires body_id")
    with _LOCK:
        if bid not in _BODIES:
            _BODIES[bid] = deepcopy(body)
        return deepcopy(_BODIES[bid])


def list_bodies() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_BODIES.items())]


def put_policy(policy: dict[str, Any]) -> dict[str, Any]:
    pid = str(policy.get("policy_id") or "")
    if not pid:
        raise ValueError("policy requires policy_id")
    with _LOCK:
        # Immutable — do not overwrite
        if pid in _POLICIES:
            return deepcopy(_POLICIES[pid])
        _POLICIES[pid] = deepcopy(policy)
        return deepcopy(_POLICIES[pid])


def get_policy(policy_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _POLICIES.get(str(policy_id or ""))
        return deepcopy(row) if row else None


def list_policies(*, domain: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_POLICIES.values())
        if domain:
            d = domain.lower()
            rows = [p for p in rows if str(p.get("domain") or "").lower() == d]
        return [
            deepcopy(p)
            for p in sorted(rows, key=lambda x: (x.get("announcement_date") or "", x.get("policy_id") or ""))
        ]


def policy_count() -> int:
    with _LOCK:
        return len(_POLICIES)


def put_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    global _TIMELINE
    with _LOCK:
        _TIMELINE = deepcopy(timeline)
        return deepcopy(_TIMELINE)


def get_timeline() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_TIMELINE) if _TIMELINE else None


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
