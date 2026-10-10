"""Thesis dependency graph — pillar propagation and committee notifications."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import PILLAR_DEPENDENCIES


def build_dependency_graph(pillars: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {p["pillar"]: p for p in pillars}
    edges = []
    for pillar, deps in PILLAR_DEPENDENCIES.items():
        for dep in deps:
            edges.append({"from": dep, "to": pillar, "relation": "informs"})

    # Propagation: weak upstream pillars discount downstream confidence
    propagation = []
    for pillar, deps in PILLAR_DEPENDENCIES.items():
        node = by_name.get(pillar)
        if not node or not deps:
            continue
        upstream_weak = [d for d in deps if float((by_name.get(d) or {}).get("strength") or 0.5) < 0.5]
        if upstream_weak:
            discount = round(0.06 * len(upstream_weak), 4)
            node["confidence"] = round(max(0.2, float(node["confidence"]) - discount), 4)
            node["confidence_pct"] = round(float(node["confidence"]) * 100)
            propagation.append(
                {
                    "pillar": pillar,
                    "weak_upstream": upstream_weak,
                    "confidence_discount": discount,
                    "note": f"{pillar} confidence discounted because upstream {', '.join(upstream_weak)} is weak",
                }
            )

    chain = "Business Quality → Financial Quality → Valuation → Portfolio Fit"
    return {
        "chain": chain,
        "edges": edges,
        "propagation": propagation,
        "committee_notifications": [
            {
                "trigger": p["note"],
                "action": "Notify Investment Committee of downstream confidence change",
            }
            for p in propagation
        ],
        "dependencies": {k: list(v) for k, v in PILLAR_DEPENDENCIES.items()},
    }
