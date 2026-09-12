"""Playbook registry index."""

from __future__ import annotations

from typing import Any

from institutional_playbooks.registry import (
    accounting,
    company,
    documents,
    government,
    industry,
    investment_committee,
    macro,
    quality,
    replay,
    valuation,
)

_MODULES = (
    company,
    valuation,
    industry,
    macro,
    government,
    documents,
    accounting,
    investment_committee,
    replay,
    quality,
)

_BY_ID: dict[str, dict[str, Any]] | None = None
_ALL: list[dict[str, Any]] | None = None


def _load() -> list[dict[str, Any]]:
    global _ALL, _BY_ID
    if _ALL is not None and _BY_ID is not None:
        return _ALL
    rows: list[dict[str, Any]] = []
    for mod in _MODULES:
        for pb in getattr(mod, "PLAYBOOKS", []) or []:
            if isinstance(pb, dict) and pb.get("playbook_id"):
                rows.append(pb)
    # Deterministic order: category then id
    rows.sort(key=lambda r: (str(r.get("category")), str(r.get("playbook_id"))))
    _ALL = rows
    _BY_ID = {str(r["playbook_id"]): r for r in rows}
    return _ALL


def list_playbooks(*, category: str | None = None) -> list[dict[str, Any]]:
    rows = _load()
    if category:
        return [r for r in rows if r.get("category") == category]
    return list(rows)


def get_playbook(playbook_id: str) -> dict[str, Any] | None:
    _load()
    assert _BY_ID is not None
    return _BY_ID.get(playbook_id)


def playbook_ids() -> list[str]:
    return [str(r["playbook_id"]) for r in list_playbooks()]


def category_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in list_playbooks():
        cat = str(r.get("category") or "unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def registry_index() -> dict[str, Any]:
    rows = list_playbooks()
    return {
        "n": len(rows),
        "counts": category_counts(),
        "playbook_ids": [r["playbook_id"] for r in rows],
        "fabricated": False,
    }
