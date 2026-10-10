"""Persistent in-process PortfolioIdea store — ideas, not positions."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()
_IDEAS: dict[str, dict[str, Any]] = {}
_VERSIONS: dict[str, list[dict[str, Any]]] = {}
_TELEMETRY: dict[str, Any] = {
    "n_creates": 0,
    "n_updates": 0,
    "n_queries": 0,
    "role_counts": Counter(),
    "sector_counts": Counter(),
    "status_counts": Counter(),
}
_RECENT: deque[dict[str, Any]] = deque(maxlen=100)


def make_idea_id(company_key: str, theme: str) -> str:
    raw = f"{company_key.strip().upper()}::{theme.strip().lower()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    slug = "".join(ch if ch.isalnum() else "-" for ch in company_key.upper())[:18].strip("-") or "IDEA"
    return f"PI-{slug}-{digest}"


def get(idea_id: str) -> dict[str, Any] | None:
    with _LOCK:
        doc = _IDEAS.get(idea_id)
        return deepcopy(doc) if doc else None


def list_ideas(
    *,
    sector: str | None = None,
    theme: str | None = None,
    role: str | None = None,
    status: str | None = None,
    company: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    with _LOCK:
        _TELEMETRY["n_queries"] = int(_TELEMETRY["n_queries"]) + 1
        rows = [deepcopy(v) for v in _IDEAS.values()]
    out = []
    for idea in rows:
        if sector and str(idea.get("sector") or "") != sector:
            continue
        if theme and str(idea.get("theme") or "") != theme:
            continue
        if role and str(idea.get("expected_role") or "") != role:
            continue
        if status and str(idea.get("status") or "") != status:
            continue
        if company and company.lower() not in str(idea.get("company") or "").lower():
            continue
        out.append(idea)
    out.sort(
        key=lambda x: (
            int(x.get("relative_rank") or 999),
            -float(x.get("conviction") or 0),
            str(x.get("company") or ""),
        )
    )
    return out[: max(1, min(limit, 200))]


def ideas_in_sector(sector: str) -> list[dict[str, Any]]:
    return list_ideas(sector=sector, limit=200)


def versions(idea_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for v in (_VERSIONS.get(idea_id) or [])]


def upsert(idea: dict[str, Any], *, is_update: bool) -> dict[str, Any]:
    iid = str(idea.get("idea_id") or "")
    if not iid:
        raise ValueError("idea_id required")
    with _LOCK:
        prev = _IDEAS.get(iid)
        snap = deepcopy(idea)
        hist = _VERSIONS.setdefault(iid, [])
        if prev is None:
            hist.append(deepcopy(snap))
            _TELEMETRY["n_creates"] = int(_TELEMETRY["n_creates"]) + 1
        else:
            if snap.get("version") != prev.get("version"):
                if not hist or hist[-1].get("version") != prev.get("version"):
                    hist.append(deepcopy(prev))
            if is_update:
                _TELEMETRY["n_updates"] = int(_TELEMETRY["n_updates"]) + 1
        _IDEAS[iid] = snap
        _TELEMETRY["role_counts"][str(snap.get("expected_role") or "?")] += 1
        _TELEMETRY["sector_counts"][str(snap.get("sector") or "?")] += 1
        _TELEMETRY["status_counts"][str(snap.get("status") or "?")] += 1
        _RECENT.appendleft(
            {
                "idea_id": iid,
                "company": snap.get("company"),
                "sector": snap.get("sector"),
                "expected_role": snap.get("expected_role"),
                "relative_rank": snap.get("relative_rank"),
                "conviction": snap.get("conviction"),
                "status": snap.get("status"),
            }
        )
        return deepcopy(snap)


def recompute_relative_ranks(sector: str) -> list[dict[str, Any]]:
    """Rank Active Consideration / Candidate ideas in a sector by conviction."""
    with _LOCK:
        rows = [
            v
            for v in _IDEAS.values()
            if str(v.get("sector") or "") == sector
            and str(v.get("status") or "") in {"Candidate", "Active Consideration"}
        ]
        rows.sort(
            key=lambda x: (
                -float(x.get("conviction") or 0),
                str(x.get("ticker") or x.get("company") or ""),
            )
        )
        updated = []
        for i, idea in enumerate(rows, start=1):
            idea["relative_rank"] = i
            idea["relative_universe_size"] = len(rows)
            _IDEAS[idea["idea_id"]] = idea
            updated.append(deepcopy(idea))
        return updated


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        return {
            "n_ideas": len(_IDEAS),
            "n_creates": int(_TELEMETRY["n_creates"]),
            "n_updates": int(_TELEMETRY["n_updates"]),
            "n_queries": int(_TELEMETRY["n_queries"]),
            "role_distribution": dict(_TELEMETRY["role_counts"]),
            "sector_distribution": dict(_TELEMETRY["sector_counts"]),
            "status_distribution": dict(_TELEMETRY["status_counts"]),
            "recent": list(_RECENT)[:10],
            "positions_stored": 0,
            "orders_stored": 0,
        }


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RECENT)[: max(1, min(limit, 100))]]
