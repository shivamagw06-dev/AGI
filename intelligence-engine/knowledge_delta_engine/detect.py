"""Change detector — classify evidence / field deltas."""

from __future__ import annotations

from typing import Any

from knowledge_delta_engine.schema import COMPARE_PATHS, DELTA_TYPES
from knowledge_delta_engine.util import approx_equal, deep_get


def classify_field(prev: Any, nxt: Any) -> str:
    if prev is None and nxt is not None:
        return "ADDED"
    if prev is not None and nxt is None:
        return "REMOVED"
    if approx_equal(prev, nxt):
        return "UNCHANGED"
    # Heuristic: string correction vs update
    if isinstance(prev, str) and isinstance(nxt, str) and prev.lower().strip() == nxt.lower().strip():
        return "CORRECTED"
    return "UPDATED"


def detect_section_changes(prev_memory: dict[str, Any] | None, next_memory: dict[str, Any]) -> dict[str, Any]:
    prev = prev_memory or {}
    sections: dict[str, Any] = {}
    for section, paths in COMPARE_PATHS.items():
        changes = []
        for path in paths:
            before = deep_get(prev, path)
            after = deep_get(next_memory, path)
            dtype = classify_field(before, after)
            if dtype == "UNCHANGED":
                continue
            item: dict[str, Any] = {
                "path": path,
                "field": path.split(".")[-1],
                "delta_type": dtype,
                "before": before,
                "after": after,
            }
            if isinstance(before, (int, float)) and isinstance(after, (int, float)) and before not in (0, None):
                item["change_pct"] = round((float(after) / float(before) - 1.0) * 100.0, 2)
                item["change_abs"] = round(float(after) - float(before), 6)
            changes.append(item)
        sections[section] = {
            "changed": bool(changes),
            "n_changes": len(changes),
            "changes": changes,
            "status": "UPDATED" if changes else "UNCHANGED",
        }
    return sections


def detect_evidence_items(
    prev_sources: list[Any] | None,
    next_sources: list[Any] | None,
) -> list[dict[str, Any]]:
    """Classify lineage / source items as ADDED/REMOVED/UNCHANGED/SUPERSEDED."""
    prev = {str(x): x for x in (prev_sources or [])}
    nxt = {str(x): x for x in (next_sources or [])}
    out = []
    for k in sorted(set(prev) | set(nxt)):
        if k in prev and k not in nxt:
            out.append({"item": k, "delta_type": "REMOVED"})
        elif k not in prev and k in nxt:
            out.append({"item": k, "delta_type": "ADDED"})
        else:
            out.append({"item": k, "delta_type": "UNCHANGED" if prev[k] == nxt[k] else "UPDATED"})
    return out


def summary_status(sections: dict[str, Any]) -> str:
    statuses = {s.get("status") for s in sections.values()}
    if statuses == {"UNCHANGED"} or not statuses:
        return "UNCHANGED"
    if "CONFLICT" in statuses:
        return "CONFLICT"
    return "UPDATED"


assert set(DELTA_TYPES)  # keep import live for validators
