"""In-memory RMS research store."""

from __future__ import annotations

from threading import RLock

from app.rms.models import ResearchObject, ResearchStatus


class RmsStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.research: dict[str, ResearchObject] = {}

    def put(self, obj: ResearchObject) -> None:
        with self._lock:
            self.research[obj.research_id] = obj

    def get(self, research_id: str) -> ResearchObject | None:
        with self._lock:
            return self.research.get(research_id)

    def list_all(self) -> list[ResearchObject]:
        with self._lock:
            return list(self.research.values())

    def list_by_status(self, *statuses: ResearchStatus) -> list[ResearchObject]:
        wanted = set(statuses)
        with self._lock:
            return [r for r in self.research.values() if r.status in wanted]

    def stats(self) -> dict[str, int]:
        with self._lock:
            by_status: dict[str, int] = {}
            for r in self.research.values():
                by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
            return {"research_objects": len(self.research), **by_status}
