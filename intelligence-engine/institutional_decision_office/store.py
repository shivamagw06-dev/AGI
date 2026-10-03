"""Persistent in-process InvestmentDecision store."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()
_DECISIONS: dict[str, dict[str, Any]] = {}
_VERSIONS: dict[str, list[dict[str, Any]]] = {}
_BY_THESIS: dict[str, str] = {}  # thesis_id -> latest decision_id
_TELEMETRY: dict[str, Any] = {
    "n_creates": 0,
    "n_updates": 0,
    "n_queries": 0,
    "decision_counts": Counter(),
    "lifecycle_counts": Counter(),
}
_RECENT: deque[dict[str, Any]] = deque(maxlen=100)


def make_decision_id(thesis_id: str, decision: str) -> str:
    raw = f"{thesis_id}::{decision}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    slug = "".join(ch if ch.isalnum() else "-" for ch in decision.upper())[:20].strip("-")
    return f"DEC-{slug}-{digest}"


def get(decision_id: str) -> dict[str, Any] | None:
    with _LOCK:
        doc = _DECISIONS.get(decision_id)
        return deepcopy(doc) if doc else None


def get_by_thesis(thesis_id: str) -> dict[str, Any] | None:
    with _LOCK:
        did = _BY_THESIS.get(thesis_id)
        if not did:
            return None
        doc = _DECISIONS.get(did)
        return deepcopy(doc) if doc else None


def list_decisions(
    *,
    decision: str | None = None,
    status: str | None = None,
    thesis_id: str | None = None,
    review_trigger: str | None = None,
    min_confidence: float | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    with _LOCK:
        _TELEMETRY["n_queries"] = int(_TELEMETRY["n_queries"]) + 1
        rows = [deepcopy(v) for v in _DECISIONS.values()]
    out = []
    for d in rows:
        if decision and str(d.get("decision") or "") != decision:
            continue
        if status and str(d.get("status") or "") != status:
            continue
        if thesis_id and str(d.get("thesis_id") or "") != thesis_id:
            continue
        if review_trigger and review_trigger.lower() not in str(d.get("review_trigger") or "").lower():
            continue
        conf = d.get("confidence")
        if min_confidence is not None and (conf is None or float(conf) < min_confidence):
            continue
        out.append(d)
    out.sort(key=lambda x: (str(x.get("company") or ""), str(x.get("decision_id") or "")))
    return out[: max(1, min(limit, 200))]


def versions(decision_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for v in (_VERSIONS.get(decision_id) or [])]


def upsert(decision: dict[str, Any], *, is_update: bool) -> dict[str, Any]:
    did = str(decision.get("decision_id") or "")
    if not did:
        raise ValueError("decision_id required")
    with _LOCK:
        prev = _DECISIONS.get(did)
        snap = deepcopy(decision)
        hist = _VERSIONS.setdefault(did, [])
        if prev is None:
            hist.append(deepcopy(snap))
            _TELEMETRY["n_creates"] = int(_TELEMETRY["n_creates"]) + 1
        else:
            if snap.get("version") != prev.get("version"):
                if not hist or hist[-1].get("version") != prev.get("version"):
                    hist.append(deepcopy(prev))
            if is_update:
                _TELEMETRY["n_updates"] = int(_TELEMETRY["n_updates"]) + 1
        _DECISIONS[did] = snap
        tid = str(snap.get("thesis_id") or "")
        if tid:
            _BY_THESIS[tid] = did
        _TELEMETRY["decision_counts"][str(snap.get("decision") or "?")] += 1
        _TELEMETRY["lifecycle_counts"][str(snap.get("status") or "?")] += 1
        _RECENT.appendleft(
            {
                "decision_id": did,
                "thesis_id": tid,
                "company": snap.get("company"),
                "decision": snap.get("decision"),
                "status": snap.get("status"),
                "confidence": snap.get("confidence"),
                "version": snap.get("version"),
            }
        )
        return deepcopy(snap)


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        return {
            "n_decisions": len(_DECISIONS),
            "n_creates": int(_TELEMETRY["n_creates"]),
            "n_updates": int(_TELEMETRY["n_updates"]),
            "n_queries": int(_TELEMETRY["n_queries"]),
            "decision_distribution": dict(_TELEMETRY["decision_counts"]),
            "lifecycle_distribution": dict(_TELEMETRY["lifecycle_counts"]),
            "recent": list(_RECENT)[:10],
        }


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RECENT)[: max(1, min(limit, 100))]]
