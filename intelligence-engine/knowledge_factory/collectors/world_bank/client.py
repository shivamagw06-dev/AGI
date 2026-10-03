"""World Bank / IMF collector — GDP and growth fixtures."""

from __future__ import annotations

from typing import Any

from knowledge_factory.collectors.base import ok_dataset
from knowledge_factory.fixtures import seed


def collect_macro() -> dict[str, Any]:
    m = seed.macro_fixture()
    return ok_dataset(
        kind="macro",
        entity="WB_MACRO",
        source="world_bank",
        payload={
            "gdp_india_growth": m["gdp_india_growth"],
            "pmi_india": m["pmi_india"],
            "oil_brent": m["oil_brent"],
        },
    )
