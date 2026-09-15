"""Derived metric store roots under FSE_STORE_ROOT."""

from __future__ import annotations

from pathlib import Path

from financial_statements_engine.store import ensure_dirs


def dme_root() -> Path:
    p = ensure_dirs() / "derived_metrics"
    for name in ("metrics", "indexes", "failures", "publications", "observability"):
        (p / name).mkdir(parents=True, exist_ok=True)
    return p
