"""Research Office telemetry helpers."""

from __future__ import annotations

from typing import Any

from research_office import store


def telemetry_board(*, limit: int = 50) -> dict[str, Any]:
    rows = store.list_telemetry(limit=limit)
    return {"n": len(rows), "items": rows, "fabricated": False}
