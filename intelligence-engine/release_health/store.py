"""Latest release-health snapshot."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

_LATEST: Optional[dict[str, Any]] = None
_HISTORY: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    global _LATEST, _HISTORY
    _LATEST = None
    _HISTORY = []


def put(snapshot: dict[str, Any]) -> dict[str, Any]:
    global _LATEST
    _LATEST = deepcopy(snapshot)
    _HISTORY.append(
        {
            "ready_for_release": snapshot.get("ready_for_release"),
            "average_benchmark": snapshot.get("average_benchmark"),
            "as_of": snapshot.get("as_of"),
        }
    )
    if len(_HISTORY) > 40:
        del _HISTORY[:-40]
    return deepcopy(_LATEST)


def latest() -> Optional[dict[str, Any]]:
    return deepcopy(_LATEST) if _LATEST else None


def metrics() -> dict[str, Any]:
    return {
        "snapshots": len(_HISTORY),
        "latest_ready": (_HISTORY[-1].get("ready_for_release") if _HISTORY else None),
        "panels": {"status": "ready" if _LATEST else "idle"},
    }
