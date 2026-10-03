"""E05-004 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e05.event_state import E05EventState


class E05StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._event: dict[tuple[str, str], E05EventState] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}

    def put(self, event: E05EventState, state: EngineState) -> None:
        key = (event.symbol.upper(), event.as_of)
        with self._lock:
            self._event[key] = event
            self._state[key] = state
            self._latest_as_of[event.symbol.upper()] = event.as_of
            hist = self._history.setdefault(event.symbol.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)

    def get_event_state(self, symbol: str, as_of: str | None = None) -> E05EventState | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._event.get((sym, day))

    def get_state(self, symbol: str, as_of: str | None = None) -> EngineState | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._state.get((sym, day))

    def history(self, symbol: str, limit: int = 50) -> list[EngineState]:
        with self._lock:
            hist = self._history.get(symbol.upper(), [])
            return list(reversed(hist[-limit:]))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "symbols": len(self._latest_as_of),
                "event_states": len(self._event),
                "states": len(self._state),
            }
