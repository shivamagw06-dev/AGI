"""E09-004 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e09.trend_state import E09State


class E09StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trend: dict[tuple[str, str], E09State] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}

    def put(self, trend: E09State, state: EngineState) -> None:
        key = (trend.symbol.upper(), trend.as_of)
        with self._lock:
            self._trend[key] = trend
            self._state[key] = state
            self._latest_as_of[trend.symbol.upper()] = trend.as_of
            hist = self._history.setdefault(trend.symbol.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)

    def get_trend_state(self, symbol: str, as_of: str | None = None) -> E09State | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._trend.get((sym, day))

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
                "trend_states": len(self._trend),
                "states": len(self._state),
            }
