"""Layer dependency edges constrained to selected participants."""

from __future__ import annotations

from typing import Any

from layer_router.registry import LAYER_DEFS

# Canonical institutional edges (sprint + registry)
_EXTRA_EDGES: list[tuple[str, str]] = [
    ("FIL", "EIL"),
    ("FIL", "ACI"),
    ("FDI", "EIL"),
    ("MII", "EIL"),
    ("MII", "Management"),
    ("EIL", "PIL"),
    ("EIL", "CIG"),
    ("EIL", "IKG"),
    ("PIL", "Valuation"),
    ("PIL", "FIE"),
    ("CIG", "Macro"),
    ("CIG", "FIE"),
    ("IKG", "ILM"),
    ("IKG", "Ownership"),
    ("ACI", "Financial"),
    ("EIL", "Business"),
    ("EIL", "Financial"),
    ("ILM", "Business"),
    ("Business", "Valuation"),
    ("Financial", "Valuation"),
    ("Financial", "Risk"),
    ("Business", "Committee"),
    ("Financial", "Committee"),
    ("Valuation", "Committee"),
    ("Risk", "Committee"),
    ("FIE", "Portfolio"),
    ("Committee", "Portfolio"),
    ("Risk", "Portfolio"),
    ("Valuation", "Portfolio"),
    ("FIE", "SSL"),
    ("Portfolio", "IDE V2"),
    ("Committee", "IDE V2"),
    ("IDE V2", "CIO"),
    ("CIO", "Research Writer"),
]


def build_dependencies(participants: list[str]) -> dict[str, Any]:
    active = set(participants)
    edges = []
    by_layer: dict[str, list[str]] = {p: [] for p in participants}
    seen = set()
    for a, b in _EXTRA_EDGES:
        if a in active and b in active and (a, b) not in seen:
            edges.append({"from": a, "to": b})
            by_layer.setdefault(b, []).append(a)
            seen.add((a, b))
    # Registry declared deps
    for name in participants:
        for dep in (LAYER_DEFS.get(name) or {}).get("dependencies") or []:
            if dep in active and (dep, name) not in seen:
                edges.append({"from": dep, "to": name})
                by_layer.setdefault(name, []).append(dep)
                seen.add((dep, name))
    return {"dependencies": by_layer, "dependency_edges": edges}
