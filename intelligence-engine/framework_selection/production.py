"""IFSE production facade."""

from __future__ import annotations

from typing import Any

from framework_selection.dashboard.board import framework_dashboard
from framework_selection.registry.frameworks import get_framework, list_frameworks
from framework_selection.schema import FREEZE_LOCKS, IFSE_VERSION, PROGRAMME
from framework_selection.selector.engine import select_frameworks
from framework_selection import store


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "ifse_version": IFSE_VERSION,
        "soft_wire_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/framework-selection",
        "fabricated": False,
    }


def select(**kwargs: Any) -> dict[str, Any]:
    out = select_frameworks(**kwargs)
    store.record_selection(out)
    return out


def registry() -> dict[str, Any]:
    rows = list_frameworks()
    return {"n": len(rows), "frameworks": rows, "ifse_version": IFSE_VERSION, "fabricated": False}


def framework(framework_id: str) -> dict[str, Any]:
    row = get_framework(framework_id)
    return {"found": bool(row), "framework": row, "fabricated": False}


def dashboard() -> dict[str, Any]:
    return framework_dashboard()


def history(*, limit: int = 50) -> dict[str, Any]:
    return {"n": min(limit, 500), "selections": store.list_selections(limit=limit), "fabricated": False}
