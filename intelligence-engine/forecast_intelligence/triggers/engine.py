"""Trigger engine — measurable, observable conditions per scenario."""

from __future__ import annotations

from typing import Any

from forecast_intelligence.schema import SCENARIO_NAMES


def triggers_for(profile: dict[str, Any]) -> dict[str, Any]:
    raw = profile.get("triggers") or {}
    matrix: dict[str, list[dict[str, Any]]] = {}
    all_observable = True
    for name in SCENARIO_NAMES:
        items = []
        for t in raw.get(name) or []:
            row = {
                "metric": t.get("metric"),
                "condition": t.get("condition"),
                "observable": bool(t.get("observable", True)),
                "monitor": f"{t.get('metric')} {t.get('condition')}",
            }
            if not row["observable"]:
                all_observable = False
            items.append(row)
        matrix[name] = items
    return {
        "matrix": matrix,
        "all_scenarios_have_triggers": all(len(matrix[n]) >= 1 for n in ("bull", "base", "bear")),
        "all_triggers_observable": all_observable and all(len(matrix[n]) >= 1 for n in SCENARIO_NAMES),
        "rule": "Triggers must be observable — no vague price targets",
    }
