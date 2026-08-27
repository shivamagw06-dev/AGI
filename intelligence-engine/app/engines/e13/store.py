"""E13-004 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e13.fundamental import E13Fundamental


class E13StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fundamental: dict[tuple[str, str], E13Fundamental] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}

    def put(self, fundamental: E13Fundamental, state: EngineState) -> None:
        key = (fundamental.symbol.upper(), fundamental.as_of)
        with self._lock:
            self._fundamental[key] = fundamental
            self._state[key] = state
            self._latest_as_of[fundamental.symbol.upper()] = fundamental.as_of
            hist = self._history.setdefault(fundamental.symbol.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)

    def get_fundamental(self, symbol: str, as_of: str | None = None) -> E13Fundamental | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._fundamental.get((sym, day))

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
                "fundamentals": len(self._fundamental),
                "states": len(self._state),
            }
