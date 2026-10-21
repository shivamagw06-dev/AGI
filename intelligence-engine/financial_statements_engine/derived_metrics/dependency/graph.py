"""Dependency graph helpers for lineage and restatement impact."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.derived_metrics.formula_registry.formulas import FORMULAS
from financial_statements_engine.derived_metrics.formula_registry.registry import get_formula_by_metric


def dependency_lineage(metric_name: str) -> dict[str, Any]:
    """Full dependency path from metric down to validated fact inputs."""
    f = get_formula_by_metric(metric_name)
    if not f:
        return {"metric": metric_name, "found": False, "path": []}

    path: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        form = get_formula_by_metric(name)
        if form:
            path.append(
                {
                    "metric": name,
                    "formula_id": form["formula_id"],
                    "formula_version": form["version"],
                    "dependencies": list(form.get("dependencies") or []),
                    "required_inputs": list(form.get("required_inputs") or []),
                }
            )
            for d in form.get("dependencies") or []:
                walk(d)
        else:
            path.append({"metric": name, "kind": "validated_fact_input"})

    walk(metric_name)
    return {"metric": metric_name, "found": True, "path": path, "complete": True}


def impacted_metrics(changed_fact_metrics: list[str]) -> list[str]:
    """Return derived metrics whose required inputs / deps touch changed facts."""
    changed = set(changed_fact_metrics)
    impacted: set[str] = set()
    # iterate until fixpoint (derived→derived)
    progress = True
    while progress:
        progress = False
        for f in FORMULAS:
            inputs = set(f.get("required_inputs") or []) | set(f.get("dependencies") or [])
            if inputs & (changed | impacted):
                if f["metric_name"] not in impacted:
                    impacted.add(f["metric_name"])
                    progress = True
    return sorted(impacted)
