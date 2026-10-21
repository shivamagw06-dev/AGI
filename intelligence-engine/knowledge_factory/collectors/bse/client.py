"""BSE collector — filings mirror (fixture-backed)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.collectors.base import ok_dataset
from knowledge_factory.fixtures import seed


def collect_filings(entity: str, *, inject: list[dict] | None = None) -> dict[str, Any]:
    e = entity.upper()
    rows = list(inject) if inject is not None else seed.filings_fixture(e)
    # Tag source bse for dual-source dedupe tests
    for r in rows:
        r = dict(r)
        r.setdefault("exchange", "BSE")
    return ok_dataset(
        kind="filings",
        entity=e,
        source="bse",
        payload={"filings": rows},
    )
