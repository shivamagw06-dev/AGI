"""IAP Mission Control soft board."""

from __future__ import annotations

from typing import Any

from institutional_playbooks.registry.index import category_counts, registry_index
from institutional_playbooks.schema import IAP_VERSION, MODULE_CODE, PROGRAMME, TARGET_COUNTS
from institutional_playbooks import store


def playbook_dashboard() -> dict[str, Any]:
    idx = registry_index()
    recent = store.list_selections(limit=20)
    counts = category_counts()
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "iap_version": IAP_VERSION,
        "registry_n": idx.get("n"),
        "category_counts": counts,
        "target_counts": TARGET_COUNTS,
        "target_met": all(counts.get(k, 0) >= v for k, v in TARGET_COUNTS.items()),
        "recent_selections": recent,
        "recent_n": len(recent),
        "soft_wire_only": True,
        "guides_reasoning": True,
        "fabricated": False,
    }
