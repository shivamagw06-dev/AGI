"""E10 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e10.portfolio import E10Portfolio


class E10StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._portfolio: dict[str, E10Portfolio] = {}  # as_of -> portfolio
        self._state: dict[str, EngineState] = {}
        self._history: list[EngineState] = []
        self._latest_as_of: str | None = None

    def put(self, portfolio: E10Portfolio, state: EngineState) -> None:
        with self._lock:
            self._portfolio[portfolio.as_of] = portfolio
            self._state[portfolio.as_of] = state
            self._latest_as_of = portfolio.as_of
            self._history = [s for s in self._history if s.as_of != state.as_of]
            self._history.append(state)
            self._history.sort(key=lambda s: s.as_of)

    def get_portfolio(self, as_of: str | None = None) -> E10Portfolio | None:
        with self._lock:
            day = as_of or self._latest_as_of
            if day is None:
                return None
            return self._portfolio.get(day)

    def get_state(self, as_of: str | None = None) -> EngineState | None:
        with self._lock:
            day = as_of or self._latest_as_of
            if day is None:
                return None
            return self._state.get(day)

    def history(self, limit: int = 50) -> list[EngineState]:
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "portfolios": len(self._portfolio),
                "states": len(self._state),
                "latest_as_of": self._latest_as_of,
            }
