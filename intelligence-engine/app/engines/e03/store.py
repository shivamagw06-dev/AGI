"""E03 persistence + warm cache."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e03.alpha import E03Alpha
from app.engines.e03.parity.audit import ParityReport


class E03StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alpha: dict[tuple[str, str], E03Alpha] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}
        self._parity: ParityReport | None = None

    def put(self, alpha: E03Alpha, state: EngineState) -> None:
        key = (alpha.symbol.upper(), alpha.as_of)
        with self._lock:
            self._alpha[key] = alpha
            self._state[key] = state
            self._latest_as_of[alpha.symbol.upper()] = alpha.as_of
            hist = self._history.setdefault(alpha.symbol.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)

    def get_alpha(self, symbol: str, as_of: str | None = None) -> E03Alpha | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._alpha.get((sym, day))

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

    def put_parity(self, report: ParityReport) -> None:
        with self._lock:
            self._parity = report

    def get_parity(self) -> ParityReport | None:
        with self._lock:
            return self._parity

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "symbols": len(self._latest_as_of),
                "alphas": len(self._alpha),
                "states": len(self._state),
                "parity_as_of": self._parity.as_of if self._parity else None,
            }
