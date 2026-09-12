"""Replay filter for playbooks — V1 playbooks are timeless procedures."""

from __future__ import annotations

from typing import Any


def filter_by_as_of(
    rows: list[dict[str, Any]],
    *,
    as_of: str | None,
    registry: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep all playbooks; procedures are not time-leaking facts."""
    _ = as_of, registry
    return list(rows), []
