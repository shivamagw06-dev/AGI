"""Versioned Research Intelligence Hub store."""

from __future__ import annotations

import copy
import time
from typing import Any

from research_intelligence_hub.schema import ResearchObject, utc_now


class ResearchHubStore:
    def __init__(self) -> None:
        self._hubs: dict[str, ResearchObject] = {}
        self._history: dict[str, list[str]] = {}  # note_id -> versioned ids
        self._order: list[str] = []
        self._runs: list[dict[str, Any]] = []
        self._version: int = 0

    def clear(self) -> None:
        self._hubs.clear()
        self._history.clear()
        self._order.clear()
        self._runs.clear()
        self._version = 0

    def publish(self, hub: ResearchObject) -> ResearchObject:
        self._version += 1
        frozen = ResearchObject.model_validate(copy.deepcopy(hub.model_dump(mode="json")))
        frozen.version = self._version
        frozen.published = True
        frozen.published_at = utc_now()
        # Keep stable note id; store under note id (latest) + versioned key
        self._hubs[frozen.id] = frozen
        vid = f"{frozen.id}@v{frozen.version}"
        self._hubs[vid] = frozen
        self._history.setdefault(frozen.id, []).append(vid)
        if frozen.id not in self._order:
            self._order.append(frozen.id)
        return frozen

    def latest(self, note_id: str | None = None) -> ResearchObject | None:
        if note_id:
            return self._hubs.get(note_id)
        if not self._order:
            return None
        return self._hubs.get(self._order[-1])

    def list_hubs(self, *, limit: int = 50) -> list[ResearchObject]:
        rows = [self._hubs[i] for i in reversed(self._order) if i in self._hubs]
        return rows[:limit]

    def history(self, note_id: str, *, limit: int = 20) -> list[ResearchObject]:
        ids = list(self._history.get(note_id) or [])
        rows = [self._hubs[i] for i in reversed(ids) if i in self._hubs]
        return rows[:limit]

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def coverage(self) -> dict[str, Any]:
        return {
            "total_hubs": len(self._order),
            "latest_version": self._version,
            "note_ids": list(self._order),
            "has_published": bool(self._order),
        }


STORE = ResearchHubStore()


def reset() -> None:
    STORE.clear()
