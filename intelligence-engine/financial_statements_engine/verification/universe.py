"""Configurable live verification universe (FSE-02.2)."""

from __future__ import annotations

import os
from typing import Any

from financial_statements_engine.verification.schema import DEFAULT_VERIFY_UNIVERSE


def resolve_verify_universe(universe: str | list[str] | None = None) -> list[str]:
    """Return ordered ticker list.

    Precedence:
    1. Explicit ``universe`` arg (comma string or list)
    2. ``FSE_VERIFY_UNIVERSE`` env (comma-separated)
    3. Default five-name production set
    """
    if universe is None:
        env = os.environ.get("FSE_VERIFY_UNIVERSE", "").strip()
        universe = env or list(DEFAULT_VERIFY_UNIVERSE)
    if isinstance(universe, str):
        parts = [p.strip().upper() for p in universe.replace(";", ",").split(",") if p.strip()]
        return parts or list(DEFAULT_VERIFY_UNIVERSE)
    return [str(t).upper().strip() for t in universe if str(t).strip()]


def universe_manifest(universe: str | list[str] | None = None) -> dict[str, Any]:
    tickers = resolve_verify_universe(universe)
    return {
        "universe": tickers,
        "n": len(tickers),
        "configurable_via": "FSE_VERIFY_UNIVERSE",
        "default": list(DEFAULT_VERIFY_UNIVERSE),
    }
