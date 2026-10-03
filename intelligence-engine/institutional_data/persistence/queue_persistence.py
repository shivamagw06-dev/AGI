"""QueuePersistence — locked RMW for the historical backfill queue."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from institutional_data.persistence.atomic import atomic_write_json, file_lock
from institutional_data.persistence.checkpoint import CheckpointManager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueuePersistence:
    """Persists queue snapshots with file locking so parallel workers cannot clobber RMW."""

    QUEUE_NAME = "historical_backfill_queue"
    ENGINE_NAME = "historical_backfill_engine_state"
    REPAIR_NAME = "coverage_repair_queue"

    def __init__(self, root: Path | str | None = None) -> None:
        self.ck = CheckpointManager(root)

    def _mirror_hd(self, report_name: str, payload: dict[str, Any]) -> None:
        """Also write into HD report store for Mission Control compatibility."""
        try:
            from knowledge_factory.historical_depth import store as hd_store

            hd_store.put_report(report_name, payload)
        except Exception:
            pass

    def load_queue(self) -> dict[str, Any]:
        local = self.ck.load(self.QUEUE_NAME)
        if local.get("companies") is not None:
            return local
        try:
            from knowledge_factory.historical_depth import queue as bf_queue

            return bf_queue.load_queue()
        except Exception:
            return {"companies": [], "updated_at": None}

    def save_queue(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.ck.path_for(self.QUEUE_NAME)
        with file_lock(path):
            body = {**payload, "updated_at": _now(), "durable": True}
            atomic_write_json(path, body)
            self._mirror_hd(self.QUEUE_NAME, body)
            return body

    def mutate_queue(self, mutator: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        """Atomic load → mutate → save under lock."""
        path = self.ck.path_for(self.QUEUE_NAME)
        with file_lock(path):
            cur = self.load_queue()
            nxt = mutator(dict(cur))
            body = {**nxt, "updated_at": _now(), "durable": True}
            atomic_write_json(path, body)
            self._mirror_hd(self.QUEUE_NAME, body)
            return body

    def load_engine(self) -> dict[str, Any]:
        local = self.ck.load(self.ENGINE_NAME)
        if local:
            return local
        try:
            from knowledge_factory.historical_depth import queue as bf_queue

            return bf_queue.load_engine_state()
        except Exception:
            return {}

    def save_engine(self, state: dict[str, Any]) -> dict[str, Any]:
        path = self.ck.path_for(self.ENGINE_NAME)
        with file_lock(path):
            body = {**state, "updated_at": _now(), "durable": True}
            atomic_write_json(path, body)
            self._mirror_hd(self.ENGINE_NAME, body)
            return body

    def save_repair_queue(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {**payload, "updated_at": _now(), "durable": True}
        self.ck.save(self.REPAIR_NAME, body)
        self._mirror_hd(self.REPAIR_NAME, body)
        return body
