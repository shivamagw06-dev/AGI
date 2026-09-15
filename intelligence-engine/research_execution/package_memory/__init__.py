"""Package memory — soft store of versioned IREP outcomes for learning hooks."""

from __future__ import annotations

from typing import Any

_MEMORY: list[dict[str, Any]] = []


def remember_package(package: dict[str, Any], *, outcome: str | None = None) -> dict[str, Any]:
    entry = {
        "package_id": package.get("package_id"),
        "version": (package.get("metadata") or {}).get("version"),
        "execution_id": (package.get("metadata") or {}).get("execution_id"),
        "question": (package.get("question") or {}).get("original"),
        "outcome": outcome or "planned",
        "learning": {
            "feed_into": "ILM",
            "immutable_plan_hash": package.get("package_id"),
        },
        "timestamp": (package.get("metadata") or {}).get("timestamp"),
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 500:
        del _MEMORY[:-500]
    return entry


def recent_packages(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_MEMORY[-limit:]))


def memory_stats() -> dict[str, Any]:
    return {"stored": len(_MEMORY), "recent": recent_packages(5)}
