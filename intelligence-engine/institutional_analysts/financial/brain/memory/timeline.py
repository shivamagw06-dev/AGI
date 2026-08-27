"""Financial Analyst memory — opinion timeline and trajectories."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_TIMELINE: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_opinion(ticker: str | None, row: dict[str, Any]) -> None:
    if not ticker:
        return
    t = ticker.upper()
    item = {**deepcopy(row), "recorded_at": _now()}
    with _LOCK:
        hist = _TIMELINE.setdefault(t, [])
        hist.append(item)
        if len(hist) > 80:
            del hist[:-80]


def get_timeline(ticker: str | None, *, limit: int = 12) -> list[dict[str, Any]]:
    if not ticker:
        return []
    with _LOCK:
        rows = list(_TIMELINE.get(ticker.upper()) or [])
    return deepcopy(rows[-limit:])


def extract_prior(previous: dict[str, Any] | None) -> dict[str, Any]:
    snap = previous if isinstance(previous, dict) else {}
    return {
        "has_prior": bool(snap),
        "prior_stance": snap.get("stance") if snap else None,
        "prior_summary": snap.get("summary") if snap else None,
        "prior_confidence": (
            (snap.get("confidence") or {}).get("overall")
            if isinstance(snap.get("confidence"), dict)
            else snap.get("confidence")
        )
        if snap
        else None,
    }


def compare_trajectory(current: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    if not prior.get("has_prior"):
        return {"trajectory": "Stable", "what_changed": [], "view_stable": True}
    changes = []
    if prior.get("prior_stance") and current.get("stance") != prior.get("prior_stance"):
        changes.append(f"Stance moved from {prior.get('prior_stance')} to {current.get('stance')}")
    comps = current.get("component_trajectories") or {}
    improving = sum(1 for v in comps.values() if v == "Improving")
    weakening = sum(1 for v in comps.values() if v == "Weakening")
    traj = "Improving" if improving > weakening else "Deteriorating" if weakening > improving else "Stable"
    if changes and traj == "Stable":
        traj = "Improving" if current.get("stance") == "Bullish" else "Deteriorating" if current.get("stance") == "Bearish" else "Stable"
    return {"trajectory": traj, "what_changed": changes, "view_stable": len(changes) == 0, "component_trajectories": comps}


def reset_for_tests() -> None:
    with _LOCK:
        _TIMELINE.clear()
