"""DME Mission Control observability counters."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.derived_metrics.formula_registry.registry import list_formulas
from financial_statements_engine.derived_metrics.store.versions import count_failures, count_stored_metrics
from financial_statements_engine.util import now_iso


def dme_metrics() -> dict[str, Any]:
    formulas = list_formulas()
    by_cat: dict[str, int] = {}
    for f in formulas:
        c = str(f.get("category") or "other")
        by_cat[c] = by_cat.get(c, 0) + 1
    return {
        "metrics_stored": count_stored_metrics(),
        "calculation_failures": count_failures(),
        "formulas_active": len(formulas),
        "formulas_by_category": by_cat,
        "as_of": now_iso(),
    }
