"""Analyst dependency graph for speaking / execution order constraints."""

from __future__ import annotations

from typing import Any

# Edges: prerequisite → dependent
_EDGES: list[tuple[str, str]] = [
    ("Business", "Valuation"),
    ("Financial", "Valuation"),
    ("Financial", "Risk"),
    ("Financial", "Accounting"),
    ("Business", "Forecast"),
    ("Financial", "Forecast"),
    ("Macro", "Forecast"),
    ("Risk", "Portfolio"),
    ("Valuation", "Portfolio"),
    ("Business", "Committee"),
    ("Financial", "Committee"),
    ("Valuation", "Committee"),
    ("Risk", "Committee"),
    ("Committee", "CIO"),
]


def build_dependencies(
    participants: list[str],
) -> dict[str, Any]:
    active = set(participants)
    edges = [{"from": a, "to": b} for a, b in _EDGES if a in active and b in active]
    by_analyst: dict[str, list[str]] = {a: [] for a in participants}
    for a, b in _EDGES:
        if a in active and b in active:
            by_analyst.setdefault(b, []).append(a)
    return {
        "dependencies": by_analyst,
        "dependency_edges": edges,
        "rules": [
            "Business must finish before Valuation",
            "Financial must finish before Risk",
            "Forecast requires Business, Financial, Macro (when present)",
        ],
        "map_version": "iar-v1",
    }
