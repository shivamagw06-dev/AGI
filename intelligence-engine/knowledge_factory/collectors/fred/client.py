"""FRED collector — US rates / inflation / unemployment."""

from __future__ import annotations

from typing import Any

from knowledge_factory.collectors.base import ok_dataset
from knowledge_factory.fixtures import seed


def collect_macro() -> dict[str, Any]:
    m = seed.macro_fixture()
    return ok_dataset(
        kind="macro",
        entity="US_MACRO",
        source="fred",
        payload={
            "us_10y": m["us_10y"],
            "us_cpi": m["us_cpi"],
            "unemployment_us": m["unemployment_us"],
        },
    )
