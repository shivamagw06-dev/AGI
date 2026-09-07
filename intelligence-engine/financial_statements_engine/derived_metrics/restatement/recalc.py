"""Restatement-driven recalculation — impact only, new versions, history preserved."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.derived_metrics.calculation.engine import calculate_company
from financial_statements_engine.derived_metrics.dependency.graph import impacted_metrics
from financial_statements_engine.derived_metrics.publication.persist import persist_calculation
from financial_statements_engine.util import now_iso


def recalculate_for_changed_facts(
    ticker: str,
    changed_fact_metrics: list[str],
    *,
    facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect impacted derived metrics and recalculate only those (plus deps)."""
    impacted = impacted_metrics(changed_fact_metrics)
    if not impacted:
        return {
            "ok": True,
            "ticker": ticker.upper().strip(),
            "impacted": [],
            "recalculated": False,
            "reason": "no_impacted_metrics",
            "as_of": now_iso(),
        }
    calc = calculate_company(ticker, metrics=impacted, facts=facts)
    persisted = persist_calculation(calc)
    publish(
        "derived_metrics.restatement_recalculated.v1",
        {
            "ticker": ticker.upper().strip(),
            "changed_fact_metrics": list(changed_fact_metrics),
            "impacted": impacted,
            "stored_n": persisted.get("stored_n"),
        },
    )
    return {
        "ok": True,
        "ticker": ticker.upper().strip(),
        "impacted": impacted,
        "recalculated": True,
        "calculation": calc,
        "persisted": persisted,
        "as_of": now_iso(),
        "mutates_warehouse_facts": False,
        "overwrites_prior_metrics": False,
    }
