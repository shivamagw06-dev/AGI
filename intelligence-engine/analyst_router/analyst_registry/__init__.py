"""Analyst registry health and lookup."""

from __future__ import annotations

from typing import Any

from analyst_router.mandates import all_mandates, get_mandate
from analyst_router.schema import ANALYST_REGISTRY, VOTING_ANALYSTS


def list_analysts() -> list[str]:
    return list(ANALYST_REGISTRY)


def registry_stats() -> dict[str, Any]:
    mandates = all_mandates()
    return {
        "count": len(ANALYST_REGISTRY),
        "analysts": list(ANALYST_REGISTRY),
        "with_mandates": len(mandates),
        "voting_analysts": sorted(VOTING_ANALYSTS),
        "complete": set(ANALYST_REGISTRY).issubset(set(mandates)),
    }


def describe(analyst: str) -> dict[str, Any]:
    m = get_mandate(analyst)
    if not m:
        return {"analyst": analyst, "known": False}
    return {
        "analyst": analyst,
        "known": True,
        "voting_rights": analyst in VOTING_ANALYSTS,
        **m,
    }
