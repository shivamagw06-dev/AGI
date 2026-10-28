"""Append-only accounting quality timeline."""

from __future__ import annotations

from typing import Any


def build_timeline(profile: dict[str, Any], *, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = list(profile.get("timeline_seed") or [])
    for e in extra or []:
        rows.append(e)
    # Deduplicate by as_of+event
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in sorted(rows, key=lambda x: str(x.get("as_of") or "")):
        key = f"{r.get('as_of')}|{r.get('event')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
