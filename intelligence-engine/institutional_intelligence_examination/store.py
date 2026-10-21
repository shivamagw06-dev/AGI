"""IIEX run store."""

from __future__ import annotations

import copy
import time
from typing import Any


class ExamStore:
    def __init__(self) -> None:
        self._runs: list[dict[str, Any]] = []

    def clear(self) -> None:
        self._runs.clear()

    def save(self, run: dict[str, Any]) -> dict[str, Any]:
        frozen = copy.deepcopy(run)
        frozen["saved_at"] = time.time()
        self._runs.append(frozen)
        if len(self._runs) > 50:
            del self._runs[:-50]
        return frozen

    def latest(self) -> dict[str, Any] | None:
        return self._runs[-1] if self._runs else None

    def history(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._runs[-limit:]))


STORE = ExamStore()


def reset() -> None:
    STORE.clear()
