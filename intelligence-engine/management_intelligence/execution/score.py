"""Execution engine — strategic initiative delivery."""

from __future__ import annotations

from typing import Any

_STATUS_SCORE = {
    "exceeded": 100.0,
    "completed": 90.0,
    "in_progress": 65.0,
    "delayed": 40.0,
    "cancelled": 10.0,
}


def execution_score(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"execution": 55.0, "items": [], "n": 0}
    vals = [_STATUS_SCORE.get(str(i.get("status") or "").lower(), 50.0) for i in items]
    score = round(sum(vals) / len(vals), 1)
    return {
        "execution": score,
        "items": items,
        "n": len(items),
        "completed": sum(1 for i in items if i.get("status") in {"completed", "exceeded"}),
        "delayed": sum(1 for i in items if i.get("status") == "delayed"),
        "cancelled": sum(1 for i in items if i.get("status") == "cancelled"),
    }
