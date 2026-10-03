"""Knowledge merge logic — never duplicate; always version; preserve history."""

from __future__ import annotations

import datetime as _dt
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def merge_string(old: str, new: str) -> str:
    old_s = (old or "").strip()
    new_s = (new or "").strip()
    if not new_s:
        return old_s
    if not old_s:
        return new_s
    if new_s.lower() == old_s.lower():
        return old_s
    # Prefer longer / more specific new content when clearly richer
    if len(new_s) >= len(old_s) + 20:
        return new_s
    return old_s


def merge_list(old: list[Any] | None, new: list[Any] | None, *, limit: int = 40) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for item in list(old or []) + list(new or []):
        if item is None:
            continue
        if isinstance(item, dict):
            key = str(item.get("ticker") or item.get("id") or item.get("title") or item).lower()
        else:
            key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:limit]


def bump_version(meta: dict[str, Any], *, reason: str) -> dict[str, Any]:
    out = dict(meta)
    out["version"] = int(out.get("version") or 1) + 1
    out["updated_at"] = _dt.datetime.now(_dt.timezone.utc)
    log = list(out.get("change_log") or [])
    log.insert(0, f"v{out['version']}: {reason}")
    out["change_log"] = log[:40]
    return out


def changed_fields(before: dict[str, Any], after: dict[str, Any], keys: list[str]) -> list[str]:
    diffs: list[str] = []
    for k in keys:
        if before.get(k) != after.get(k):
            diffs.append(k)
    return diffs
