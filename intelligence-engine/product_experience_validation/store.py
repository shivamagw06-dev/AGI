"""In-memory store for latest E2E-01 run."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

_LATEST: Optional[dict[str, Any]] = None
_HISTORY: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    global _LATEST, _HISTORY
    _LATEST = None
    _HISTORY = []


def put_run(result: dict[str, Any]) -> dict[str, Any]:
    global _LATEST
    _LATEST = deepcopy(result)
    _HISTORY.append(
        {
            "passed": result.get("passed"),
            "score": result.get("score"),
            "as_of": result.get("as_of"),
            "failure_codes": list(result.get("failure_codes") or []),
        }
    )
    if len(_HISTORY) > 40:
        del _HISTORY[:-40]
    return deepcopy(_LATEST)


def latest() -> Optional[dict[str, Any]]:
    return deepcopy(_LATEST) if _LATEST else None


def metrics() -> dict[str, Any]:
    runs = list(_HISTORY)
    passed = sum(1 for r in runs if r.get("passed"))
    return {
        "runs": len(runs),
        "passed": passed,
        "failed": len(runs) - passed,
        "latest_score": (runs[-1].get("score") if runs else None),
        "panels": {
            "status": "ready",
            "pass_rate": round(passed / len(runs), 4) if runs else None,
        },
    }
