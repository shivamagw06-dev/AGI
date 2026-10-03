"""Why a multiple moved.

Terminals report that P/E fell from 18.4 to 17.9 and leave the analyst to work
out why. Because every figure here declares what it was computed from, the
cause is derivable: compare each input across two observations and name the
ones that actually moved.

The engine states the arithmetic — price fell, earnings did not — and stops
there. Why the price fell is a question for the research layer, not this one.
"""

from __future__ import annotations

from typing import Any, Optional

from valuation_engine import graph

#: Below this, an input counts as unchanged. Prices carry noise; a multiple
#: that moved 0.1% did not move for a reason worth narrating.
MATERIAL_PCT = 0.5


def _pct_change(before: Any, after: Any) -> Optional[float]:
    try:
        start, end = float(before), float(after)
    except (TypeError, ValueError):
        return None
    if start == 0:
        return None
    return round(100.0 * (end - start) / abs(start), 3)


def _describe(name: str, change: float) -> str:
    direction = "rose" if change > 0 else "declined"
    return f"{name.replace('_', ' ')} {direction} {abs(change):.1f}%"


def explain_change(metric: str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Attribute a metric's move to the inputs that actually changed.

    ``before`` and ``after`` are flat metric -> value maps for two observations
    of one company.
    """
    metric_change = _pct_change(before.get(metric), after.get(metric))
    inputs = graph.inputs_of(metric)

    moved: list[dict[str, Any]] = []
    unchanged: list[str] = []
    unknown: list[str] = []

    for name in inputs:
        change = _pct_change(before.get(name), after.get(name))
        if change is None:
            unknown.append(name)
        elif abs(change) >= MATERIAL_PCT:
            moved.append({"input": name, "change_pct": change,
                          "from": before.get(name), "to": after.get(name)})
        else:
            unchanged.append(name)

    if metric_change is None:
        summary = f"{metric} could not be compared across the two observations."
    elif not moved and not unknown:
        summary = (f"{metric} is effectively unchanged; no input moved more than "
                   f"{MATERIAL_PCT}%.")
    elif len(moved) == 1:
        driver = moved[0]
        held = f"{', '.join(unchanged)} unchanged" if unchanged else "no other input moved"
        summary = (f"{metric} moved {metric_change:+.1f}% because "
                   f"{_describe(driver['input'], driver['change_pct'])}, with {held}.")
    elif moved:
        drivers = "; ".join(_describe(m["input"], m["change_pct"]) for m in moved)
        summary = f"{metric} moved {metric_change:+.1f}% as {drivers}."
    else:
        summary = (
            f"{metric.upper()} moved {metric_change:+.1f}% but price/earnings attribution "
            f"could not be decomposed ({', '.join(unknown)} unavailable)."
        )

    return {
        "metric": metric,
        "change_pct": metric_change,
        "from": before.get(metric),
        "to": after.get(metric),
        "drivers": sorted(moved, key=lambda m: -abs(m["change_pct"])),
        "unchanged": unchanged,
        "uncomparable": unknown,
        "summary": summary,
    }


def change_log(before: dict[str, Any], after: dict[str, Any],
               *, metrics: Optional[list[str]] = None) -> dict[str, Any]:
    """Attribution for every multiple that moved between two observations."""
    wanted = metrics or ["pe", "pb", "ev_ebitda", "ev_sales", "ps",
                         "market_cap", "enterprise_value", "dividend_yield"]
    entries = []
    for metric in wanted:
        if before.get(metric) is None and after.get(metric) is None:
            continue
        entry = explain_change(metric, before, after)
        if entry["change_pct"] is None or abs(entry["change_pct"]) < MATERIAL_PCT:
            continue
        entries.append(entry)
    return {
        "ok": True,
        "material_pct": MATERIAL_PCT,
        "changed": len(entries),
        "entries": sorted(entries, key=lambda e: -abs(e["change_pct"] or 0.0)),
    }
