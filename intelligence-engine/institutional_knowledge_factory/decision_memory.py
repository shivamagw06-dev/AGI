"""Decision memory — explainable assertion evolution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_MEMORY: dict[str, list[dict[str, Any]]] = {}


def _key(entity_id: str) -> str:
    return entity_id.upper()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def record_decision_memory(
    entity_id: str,
    *,
    changes: list[dict[str, Any]] | None = None,
    thesis: dict[str, Any] | None = None,
    source: str = "evidence_pipeline",
    research_conclusion: str | None = None,
) -> dict[str, Any]:
    """Append decision memory entry for an entity."""
    entry = {
        "entity_id": entity_id.upper(),
        "timestamp": _now_iso(),
        "source": source,
        "assertion_changes": list(changes or []),
        "thesis_snapshot": thesis,
        "research_conclusion": research_conclusion,
        "change_count": len(changes or []),
    }
    key = _key(entity_id)
    _MEMORY.setdefault(key, []).append(entry)
    return entry


def get_decision_memory(entity_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    return list(_MEMORY.get(_key(entity_id), [])[-limit:])


def version_decision_memory(
    entity_id: str,
    iko: dict[str, Any],
    changes: list[dict[str, Any]],
    thesis: dict[str, Any],
) -> dict[str, Any]:
    """Version decision memory and attach refs to IKO."""
    entry = record_decision_memory(
        entity_id,
        changes=changes,
        thesis=thesis,
        source="evidence_pipeline",
    )
    refs = list(iko.get("decision_memory_refs") or [])
    refs.append({"memory_id": f"DM_{entity_id}_{len(refs)}", "timestamp": entry["timestamp"]})
    iko = dict(iko)
    iko["decision_memory_refs"] = refs[-50:]
    return iko
