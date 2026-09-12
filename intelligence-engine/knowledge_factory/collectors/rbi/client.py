"""RBI collector — repo, inflation, liquidity, FX."""

from __future__ import annotations

from typing import Any

from knowledge_factory.collectors.base import ok_dataset
from knowledge_factory.fixtures import seed


def collect_macro() -> dict[str, Any]:
    m = seed.macro_fixture()
    return ok_dataset(
        kind="macro",
        entity="IN_MACRO",
        source="rbi",
        payload={
            "repo_rate": m["repo_rate"],
            "cpi": m["cpi"],
            "usd_inr": m["usd_inr"],
            "liquidity": "normal",
        },
    )
