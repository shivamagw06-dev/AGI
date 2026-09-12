"""Institutional Evaluation Suite (IES) — AGIB's institutional finance benchmark.

Soft-wire under institutional_reasoning. Not a new top-level engine.
Equivalent role to MMLU / SWE-bench / GAIA — for institutional finance.
"""

from __future__ import annotations

from institutional_reasoning.ies.production import (
    dashboard,
    inventory,
    quality_gates,
    run_ies,
)

__all__ = ["dashboard", "inventory", "quality_gates", "run_ies"]
