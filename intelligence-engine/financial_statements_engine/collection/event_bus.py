"""Evidence Event Bus — decouples collectors from parsers (FSE-02 §4).

v1: durable JSONL log + in-process subscribers. At-least-once delivery.
Collector failures must not be caused by subscriber exceptions.
"""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

from financial_statements_engine.collection.schema import EVENT_TYPES
from financial_statements_engine.store import ensure_dirs, store_root
from financial_statements_engine.util import now_iso, write_json_atomic

Subscriber = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Subscriber]] = {}
        self._lock = threading.Lock()

    def _log_path(self) -> Path:
        root = ensure_dirs()
        path = root / "events" / "bus.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _cursor_path(self, subscriber_id: str) -> Path:
        root = ensure_dirs()
        d = root / "events" / "cursors"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{subscriber_id}.json"

    def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {event_type}")
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "ts": now_iso(),
            "payload": payload or {},
        }
        line = json.dumps(event, sort_keys=True, default=str)
        with self._lock:
            with self._log_path().open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            handlers = list(self._subs.get(event_type, [])) + list(self._subs.get("*", []))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # At-least-once bus must not fail the collector
                continue
        return event

    def subscribe(self, event_type: str, handler: Subscriber, *, subscriber_id: str | None = None) -> None:
        if event_type != "*" and event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {event_type}")
        with self._lock:
            self._subs.setdefault(event_type, []).append(handler)
        if subscriber_id:
            write_json_atomic(
                self._cursor_path(subscriber_id),
                {"subscriber_id": subscriber_id, "event_type": event_type, "subscribed_at": now_iso()},
            )

    def tail(self, limit: int = 50) -> list[dict[str, Any]]:
        path = self._log_path()
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-max(1, int(limit)) :]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def stats(self) -> dict[str, Any]:
        path = self._log_path()
        n = 0
        by_type: dict[str, int] = {}
        if path.exists():
            for line in path.open(encoding="utf-8"):
                n += 1
                try:
                    ev = json.loads(line)
                    t = str(ev.get("event_type") or "unknown")
                    by_type[t] = by_type.get(t, 0) + 1
                except json.JSONDecodeError:
                    continue
        return {
            "events_total": n,
            "by_type": by_type,
            "log_path": str(path),
            "store_root": str(store_root()),
        }


_BUS = EventBus()


def get_bus() -> EventBus:
    return _BUS


def publish(event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return _BUS.publish(event_type, payload)


def subscribe(event_type: str, handler: Subscriber, *, subscriber_id: str | None = None) -> None:
    _BUS.subscribe(event_type, handler, subscriber_id=subscriber_id)


def reset_bus_for_tests() -> EventBus:
    """Replace process-global bus (tests only)."""
    global _BUS
    _BUS = EventBus()
    return _BUS
