"""Duplicate detection within a parse — flag only, do not drop."""

from __future__ import annotations

from typing import Any


def detect_duplicates(mapped_metrics: dict[str, Any]) -> dict[str, Any]:
    """Flag duplicate canonical metrics if multiple source labels collapsed oddly.

    Mapped metrics should already be unique by canonical key; this detects
    when source retained parallel entries in ``collisions``.
    """
    flags: list[dict[str, Any]] = []
    for metric, row in (mapped_metrics or {}).items():
        if isinstance(row, dict) and row.get("duplicate_sources"):
            flags.append(
                {
                    "metric": metric,
                    "sources": row.get("duplicate_sources"),
                    "code": "duplicate_metric",
                }
            )
    return {
        "duplicate_flags": flags,
        "has_duplicates": bool(flags),
        "layer": "duplicate_detection",
    }
