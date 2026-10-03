"""In-process CTI trigger state store — lifecycle tracking."""

from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any


class TriggerStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._triggers: dict[str, dict[str, Any]] = {}
        self._evaluations: list[dict[str, Any]] = []

    def upsert(self, trigger: dict[str, Any]) -> dict[str, Any]:
        tid = trigger["trigger_id"]
        with self._lock:
            prev = self._triggers.get(tid)
            if prev:
                # Preserve lifecycle unless explicitly advanced
                trigger = {
                    **trigger,
                    "state": trigger.get("state") or prev.get("state"),
                    "history": list(prev.get("history") or []) + list(trigger.get("history") or []),
                }
            self._triggers[tid] = trigger
            return deepcopy(trigger)

    def get(self, trigger_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._triggers.get(trigger_id)
            return deepcopy(row) if row else None

    def list_for_entity(self, entity: str) -> list[dict[str, Any]]:
        e = (entity or "").upper()
        with self._lock:
            rows = [deepcopy(t) for t in self._triggers.values() if str(t.get("entity") or "").upper() == e]
        return sorted(rows, key=lambda t: (_priority_rank(t.get("priority")), t.get("trigger_id") or ""))

    def list_all(self, *, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(t) for t in self._triggers.values()]
        rows.sort(key=lambda t: (_priority_rank(t.get("priority")), t.get("trigger_id") or ""))
        return rows[:limit]

    def set_state(self, trigger_id: str, state: str, *, note: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            row = self._triggers.get(trigger_id)
            if not row:
                return None
            hist = list(row.get("history") or [])
            hist.append({"from": row.get("state"), "to": state, "note": note})
            row["state"] = state
            row["history"] = hist[-20:]
            self._triggers[trigger_id] = row
            return deepcopy(row)

    def record_evaluation(self, evaluation: dict[str, Any]) -> None:
        with self._lock:
            self._evaluations.append(evaluation)
            if len(self._evaluations) > 200:
                self._evaluations = self._evaluations[-200:]

    def recent_evaluations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._evaluations[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._triggers.clear()
            self._evaluations.clear()


_STORE: TriggerStore | None = None


def get_store() -> TriggerStore:
    global _STORE
    if _STORE is None:
        _STORE = TriggerStore()
    return _STORE


def _priority_rank(priority: Any) -> int:
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    return order.get(str(priority), 9)
