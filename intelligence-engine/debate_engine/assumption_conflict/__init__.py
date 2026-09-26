"""Assumption conflict detection across analyst positions."""

from __future__ import annotations

from typing import Any

_STRUCTURED_CONFLICTS = (
    (
        "Business",
        "Macro",
        "The competitive moat remains durable",
        "The macro regime may intensify deposit competition",
        "Funding advantage",
    ),
    (
        "Business",
        "Valuation",
        "Durable quality creates investment value",
        "Current quality may already be fully priced",
        "Investment attractiveness",
    ),
    (
        "Financial",
        "Risk",
        "Financial resilience persists through-cycle",
        "Downside scenarios may breach current resilience",
        "Loss absorption",
    ),
    (
        "Valuation",
        "Portfolio",
        "Standalone expected return justifies exposure",
        "Portfolio concentration may dominate standalone return",
        "Portfolio fit",
    ),
)


def find_assumption_conflicts(
    positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_analyst = {p["analyst"]: p for p in positions}
    out = []
    for i, (a, b, assumption_a, assumption_b, topic) in enumerate(
        _STRUCTURED_CONFLICTS, start=1
    ):
        if a not in by_analyst or b not in by_analyst:
            continue
        out.append(
            {
                "id": f"AC-{i:03d}",
                "topic": topic,
                "analyst_a": a,
                "assumption_a": assumption_a,
                "analyst_b": b,
                "assumption_b": assumption_b,
                "challenged": True,
                "resolution_question": (
                    f"Which assumption about {topic.lower()} is best supported by independent evidence?"
                ),
                "required_evidence": list(
                    dict.fromkeys(
                        (by_analyst[a].get("required_evidence") or [])
                        + (by_analyst[b].get("required_evidence") or [])
                    )
                )[:4],
            }
        )
    return out
