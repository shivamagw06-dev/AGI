"""Point-in-time filter: available_from <= as_of."""

from __future__ import annotations

from typing import Any


def filter_by_as_of(
    frameworks: list[dict[str, Any]],
    *,
    as_of: str | None,
    registry: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not as_of:
        return frameworks, []
    as_of_day = str(as_of)[:10]
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for row in frameworks:
        fid = row.get("framework_id")
        meta = registry.get(str(fid)) or {}
        avail = str(meta.get("available_from") or "1990-01-01")[:10]
        if avail <= as_of_day and meta.get("replay_compatibility", True):
            kept.append(row)
        else:
            dropped.append(str(fid))
    return kept, dropped
