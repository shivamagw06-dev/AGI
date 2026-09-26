"""NSE collector — announcements / filings / corporate actions (fixture-backed)."""

from __future__ import annotations

import os
from typing import Any

from knowledge_factory.collectors.base import ok_dataset, unavailable
from knowledge_factory.fixtures import seed


def collect_filings(entity: str, *, live: bool | None = None, inject: list[dict] | None = None) -> dict[str, Any]:
    live = bool(os.environ.get("KF_LIVE_NSE")) if live is None else live
    e = entity.upper()
    if live:
        return unavailable("nse", e, "nse_live_not_configured")
    rows = list(inject) if inject is not None else seed.filings_fixture(e)
    return ok_dataset(
        kind="filings",
        entity=e,
        source="nse",
        payload={"filings": rows, "shareholding": {}, "board_changes": []},
    )
