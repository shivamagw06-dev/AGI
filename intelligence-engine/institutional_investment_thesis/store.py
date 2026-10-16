"""Persistent in-process Investment Thesis store (living objects + versions)."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()
# thesis_id -> current thesis document
_THESES: dict[str, dict[str, Any]] = {}
# thesis_id -> list of version snapshots (oldest first)
_VERSIONS: dict[str, list[dict[str, Any]]] = {}
_TELEMETRY: dict[str, Any] = {
    "n_creates": 0,
    "n_updates": 0,
    "n_queries": 0,
    "lifecycle_counts": Counter(),
    "decision_counts": Counter(),
}
_RECENT: deque[dict[str, Any]] = deque(maxlen=100)


def _stable_thesis_id(company_key: str, question: str) -> str:
    raw = f"{company_key.strip().upper()}::{question.strip().lower()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    slug = "".join(ch if ch.isalnum() else "-" for ch in company_key.upper())[:24].strip("-") or "THESIS"
    return f"TH-{slug}-{digest}"


def make_thesis_id(company: str | None, ticker: str | None, question: str) -> str:
    key = (ticker or company or "CONCEPT").strip() or "CONCEPT"
    return _stable_thesis_id(key, question)


def get(thesis_id: str) -> dict[str, Any] | None:
    with _LOCK:
        doc = _THESES.get(thesis_id)
        return deepcopy(doc) if doc else None


def list_theses(
    *,
    status: str | None = None,
    lifecycle: str | None = None,
    decision_status: str | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    waiting_for: str | None = None,
    confidence_drop_gt: float | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    with _LOCK:
        _TELEMETRY["n_queries"] = int(_TELEMETRY["n_queries"]) + 1
        rows = [deepcopy(v) for v in _THESES.values()]
    out: list[dict[str, Any]] = []
    for t in rows:
        if status and str(t.get("status") or "") != status:
            continue
        if lifecycle and str(t.get("lifecycle") or "") != lifecycle:
            continue
        if decision_status and str(t.get("decision_status") or "") != decision_status:
            continue
        conf = t.get("confidence")
        if min_confidence is not None and (conf is None or float(conf) < min_confidence):
            continue
        if max_confidence is not None and (conf is None or float(conf) > max_confidence):
            continue
        if waiting_for:
            mon = " ".join(str(x) for x in (t.get("monitoring_checklist") or [])).lower()
            if waiting_for.lower() not in mon:
                continue
        if confidence_drop_gt is not None:
            drop = t.get("confidence_change")
            if drop is None or float(drop) > -abs(float(confidence_drop_gt)):
                # want drop more than N points → change <= -N
                continue
        out.append(t)
    out.sort(key=lambda x: (str(x.get("company") or ""), str(x.get("thesis_id") or "")))
    return out[: max(1, min(limit, 200))]


def versions(thesis_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for v in (_VERSIONS.get(thesis_id) or [])]


def upsert(thesis: dict[str, Any], *, is_update: bool) -> dict[str, Any]:
    tid = str(thesis.get("thesis_id") or "")
    if not tid:
        raise ValueError("thesis_id required")
    with _LOCK:
        prev = _THESES.get(tid)
        snap = deepcopy(thesis)
        hist = _VERSIONS.setdefault(tid, [])
        if prev is None:
            snap["confidence_change"] = 0.0
            hist.append(deepcopy(snap))
            _TELEMETRY["n_creates"] = int(_TELEMETRY["n_creates"]) + 1
        else:
            try:
                prev_c = float(prev.get("confidence") or 0)
                cur_c = float(snap.get("confidence") or 0)
                snap["confidence_change"] = round(cur_c - prev_c, 2)
            except (TypeError, ValueError):
                snap["confidence_change"] = 0.0
            # Keep prior version snapshot when version advances
            if snap.get("version") != prev.get("version"):
                if not hist or hist[-1].get("version") != prev.get("version"):
                    hist.append(deepcopy(prev))
            if is_update:
                _TELEMETRY["n_updates"] = int(_TELEMETRY["n_updates"]) + 1
        _THESES[tid] = snap
        _TELEMETRY["lifecycle_counts"][str(snap.get("lifecycle") or "?")] += 1
        _TELEMETRY["decision_counts"][str(snap.get("decision_status") or "?")] += 1
        _RECENT.appendleft(
            {
                "thesis_id": tid,
                "company": snap.get("company"),
                "lifecycle": snap.get("lifecycle"),
                "decision_status": snap.get("decision_status"),
                "confidence": snap.get("confidence"),
                "version": snap.get("version"),
            }
        )
        return deepcopy(snap)


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        return {
            "n_theses": len(_THESES),
            "n_creates": int(_TELEMETRY["n_creates"]),
            "n_updates": int(_TELEMETRY["n_updates"]),
            "n_queries": int(_TELEMETRY["n_queries"]),
            "lifecycle_distribution": dict(_TELEMETRY["lifecycle_counts"]),
            "decision_distribution": dict(_TELEMETRY["decision_counts"]),
            "recent": list(_RECENT)[:10],
        }


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RECENT)[: max(1, min(limit, 100))]]
