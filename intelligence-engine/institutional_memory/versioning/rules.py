"""Append-only versioning — never overwrite theses / decisions / forecasts."""

from __future__ import annotations

from typing import Any


def next_version(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 1
    versions = [int(r.get("version") or 0) for r in rows]
    return max(versions) + 1


def assert_append_only(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify versions are unique and monotonically increasing; no in-place overwrite."""
    seen: set[int] = set()
    last = 0
    ok = True
    issues: list[str] = []
    for r in sorted(rows, key=lambda x: int(x.get("version") or 0)):
        v = int(r.get("version") or 0)
        if v in seen:
            ok = False
            issues.append(f"duplicate_version:{v}")
        if v < last:
            ok = False
            issues.append(f"non_monotonic:{v}<{last}")
        seen.add(v)
        last = v
        if r.get("overwritten") is True:
            ok = False
            issues.append(f"overwritten_flag:{v}")
    return {
        "append_only": ok,
        "no_overwrite": ok and not any(r.get("overwritten") for r in rows),
        "version_count": len(rows),
        "issues": issues,
    }
