"""E01 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState


class E01StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: EngineState | None = None
        self._history: list[EngineState] = []
        self._by_as_of: dict[str, EngineState] = {}

    def put(self, state: EngineState) -> None:
        with self._lock:
            self._current = state
            self._by_as_of[state.as_of] = state
            # Keep chronological unique as_of history
            self._history = [s for s in self._history if s.as_of != state.as_of]
            self._history.append(state)
            self._history.sort(key=lambda s: s.as_of)

    def current(self) -> EngineState | None:
        with self._lock:
            return self._current

    def get(self, as_of: str) -> EngineState | None:
        with self._lock:
            return self._by_as_of.get(as_of)

    def history(self, limit: int = 50) -> list[EngineState]:
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "has_current": self._current is not None,
                "history_len": len(self._history),
                "current_as_of": self._current.as_of if self._current else None,
            }
