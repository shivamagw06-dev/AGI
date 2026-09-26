"""L4 persistence + warm cache (shadow tables only)."""

from __future__ import annotations

import threading
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.l4.opinion import L4Opinion
from app.engines.l4.shadow import ShadowComparison


class L4StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._opinion: dict[tuple[str, str], L4Opinion] = {}
        self._state: dict[tuple[str, str], EngineState] = {}
        self._history: dict[str, list[EngineState]] = {}
        self._latest_as_of: dict[str, str] = {}
        self._shadow: dict[tuple[str, str], ShadowComparison] = {}
        self._latest_shadow: dict[str, str] = {}

    def put(
        self,
        opinion: L4Opinion,
        state: EngineState,
        shadow: ShadowComparison | None = None,
    ) -> None:
        key = (opinion.symbol.upper(), opinion.as_of)
        with self._lock:
            self._opinion[key] = opinion
            self._state[key] = state
            self._latest_as_of[opinion.symbol.upper()] = opinion.as_of
            hist = self._history.setdefault(opinion.symbol.upper(), [])
            hist[:] = [s for s in hist if s.as_of != state.as_of]
            hist.append(state)
            hist.sort(key=lambda s: s.as_of)
            if shadow is not None:
                self._shadow[key] = shadow
                self._latest_shadow[opinion.symbol.upper()] = opinion.as_of

    def get_opinion(self, symbol: str, as_of: str | None = None) -> L4Opinion | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._opinion.get((sym, day))

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

    def get_shadow(self, symbol: str, as_of: str | None = None) -> ShadowComparison | None:
        sym = symbol.upper()
        with self._lock:
            day = as_of or self._latest_shadow.get(sym) or self._latest_as_of.get(sym)
            if day is None:
                return None
            return self._shadow.get((sym, day))

    def list_opinions(self, as_of: str | None = None) -> dict[str, L4Opinion]:
        """Latest opinion per symbol, optionally filtered to a single as_of day."""
        with self._lock:
            out: dict[str, L4Opinion] = {}
            for sym, day in self._latest_as_of.items():
                use_day = as_of or day
                op = self._opinion.get((sym, use_day))
                if op is not None:
                    out[sym] = op
            return out

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "symbols": len(self._latest_as_of),
                "opinions": len(self._opinion),
                "states": len(self._state),
                "shadow_rows": len(self._shadow),
            }
