"""E04-004 persistence + warm cache (keyed by pair_id)."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e04.rv_state import E04State


class E04StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rv: dict[tuple[str, str], E04State] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}

    def put(self, rv: E04State, state: EngineState) -> None:
        key = (rv.pair_id.upper(), rv.as_of)
        with self._lock:
            self._rv[key] = rv
            self._state[key] = state
            self._latest_as_of[rv.pair_id.upper()] = rv.as_of
            hist = self._history.setdefault(rv.pair_id.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)

    def get_rv_state(self, pair: str, as_of: str | None = None) -> E04State | None:
        pid = pair.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(pid)
            if day is None:
                return None
            return self._rv.get((pid, day))

    def get_state(self, pair: str, as_of: str | None = None) -> EngineState | None:
        pid = pair.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(pid)
            if day is None:
                return None
            return self._state.get((pid, day))

    def history(self, pair: str, limit: int = 50) -> list[EngineState]:
        with self._lock:
            hist = self._history.get(pair.upper(), [])
            return list(reversed(hist[-limit:]))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pairs": len(self._latest_as_of),
                "rv_states": len(self._rv),
                "states": len(self._state),
            }
