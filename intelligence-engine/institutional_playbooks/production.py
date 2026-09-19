"""IAP production facade."""

from __future__ import annotations

from typing import Any

from institutional_playbooks.dashboard.board import playbook_dashboard
from institutional_playbooks.registry.index import get_playbook, list_playbooks, registry_index
from institutional_playbooks.schema import FREEZE_LOCKS, IAP_VERSION, PROGRAMME
from institutional_playbooks.selector.engine import select_playbook
from institutional_playbooks import store


def health() -> dict[str, Any]:
    idx = registry_index()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "iap_version": IAP_VERSION,
        "registry_n": idx.get("n"),
        "soft_wire_only": True,
        "guides_reasoning": True,
        "replaces_reasoning": False,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/institutional-playbooks",
        "fabricated": False,
    }


def select(**kwargs: Any) -> dict[str, Any]:
    out = select_playbook(**kwargs)
    store.record_selection(out)
    return out


def registry() -> dict[str, Any]:
    rows = list_playbooks()
    slim = [
        {
            "playbook_id": r.get("playbook_id"),
            "name": r.get("name"),
            "category": r.get("category"),
            "priority": r.get("priority"),
            "n_checklist": len(r.get("checklist") or []),
            "n_procedure": len(r.get("procedure") or []),
            "frameworks": r.get("frameworks"),
        }
        for r in rows
    ]
    return {
        "n": len(slim),
        "counts": registry_index().get("counts"),
        "playbooks": slim,
        "iap_version": IAP_VERSION,
        "fabricated": False,
    }


def playbook(playbook_id: str) -> dict[str, Any]:
    row = get_playbook(playbook_id)
    return {"found": bool(row), "playbook": row, "fabricated": False}


def dashboard() -> dict[str, Any]:
    return playbook_dashboard()


def history(*, limit: int = 50) -> dict[str, Any]:
    return {"n": min(limit, 500), "selections": store.list_selections(limit=limit), "fabricated": False}
