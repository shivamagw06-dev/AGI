"""Formula Registry service — central catalogue + dependency order."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.derived_metrics.formula_registry.formulas import FORMULAS, build_registry

FORMULA_REGISTRY: dict[str, dict[str, Any]] = build_registry()


def get_formula(formula_id: str) -> dict[str, Any] | None:
    return FORMULA_REGISTRY.get(formula_id)


def get_formula_by_metric(metric_name: str) -> dict[str, Any] | None:
    for f in FORMULA_REGISTRY.values():
        if f.get("metric_name") == metric_name and f.get("status") == "active":
            return f
    return None


def list_formulas(*, category: str | None = None) -> list[dict[str, Any]]:
    rows = list(FORMULA_REGISTRY.values())
    if category:
        rows = [r for r in rows if r.get("category") == category]
    return sorted(rows, key=lambda r: (str(r.get("category")), str(r.get("metric_name"))))


def resolve_order(metric_names: list[str] | None = None) -> list[str]:
    """Topological order of metric names. Raises on cycles."""
    wanted = set(metric_names) if metric_names else {f["metric_name"] for f in FORMULAS}
    # include dependencies transitively
    changed = True
    while changed:
        changed = False
        for f in FORMULAS:
            if f["metric_name"] in wanted:
                for d in f.get("dependencies") or []:
                    if d not in wanted:
                        wanted.add(d)
                        changed = True

    deps: dict[str, set[str]] = {}
    for f in FORMULAS:
        m = f["metric_name"]
        if m not in wanted:
            continue
        deps[m] = set(f.get("dependencies") or [])

    ordered: list[str] = []
    remaining = set(deps)
    while remaining:
        ready = sorted(m for m in remaining if deps[m].isdisjoint(remaining))
        if not ready:
            raise ValueError(f"circular_dependencies: {sorted(remaining)}")
        for m in ready:
            ordered.append(m)
            remaining.remove(m)
    return ordered
