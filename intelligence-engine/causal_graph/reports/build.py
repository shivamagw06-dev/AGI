"""Narrative / table builders for desks, committee, CIO, research writer."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    ticker: str | None = None,
    company_pack: dict[str, Any] | None = None,
    event_pack: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    counterfactual: dict[str, Any] | None = None,
    portfolio_impact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    company_pack = company_pack or {}
    event_pack = event_pack or {}
    chains = company_pack.get("chains") or event_pack.get("chains") or []
    upstream = company_pack.get("upstream_drivers") or []
    strongest = sorted(
        chains,
        key=lambda c: (-float(c.get("transmission_probability") or 0), -float(c.get("path_confidence") or 0)),
    )[:5]
    weakest = sorted(
        chains,
        key=lambda c: (float(c.get("transmission_probability") or 0), float(c.get("path_confidence") or 0)),
    )[:3]

    why_lines = []
    if ticker and upstream:
        why_lines.append(
            f"{ticker.upper()} moves are better explained by upstream drivers {', '.join(upstream[:4])} than by isolated price action."
        )
    if company_pack.get("sector_model"):
        why_lines.append(
            f"Sector model: {(company_pack.get('sector_model') or {}).get('narrative')}"
        )
    if event_pack.get("found"):
        why_lines.append(
            f"Event {event_pack.get('label')}: primary→secondary→third-order transmission across "
            f"{len(event_pack.get('affected_sectors') or [])} sectors."
        )
    if not why_lines:
        why_lines.append("Causal graph explains market moves as evidenced transmission chains, not isolated events.")

    propagation_table = [
        {
            "order": c.get("order_label"),
            "path": " → ".join(c.get("path_labels") or c.get("path") or []),
            "probability": c.get("transmission_probability"),
            "confidence": c.get("path_confidence"),
            "direction": c.get("effect_direction") or ("up" if (c.get("net_direction_sign") or 1) > 0 else "down"),
        }
        for c in (event_pack.get("chains") or chains)[:12]
    ]

    return {
        "executive_summary": " ".join(why_lines),
        "why_this_happened": why_lines,
        "upstream_drivers": upstream,
        "strongest_drivers": [
            {"path": " → ".join(c.get("path_labels") or []), "p": c.get("transmission_probability")}
            for c in strongest
        ],
        "weakest_drivers": [
            {"path": " → ".join(c.get("path_labels") or []), "p": c.get("transmission_probability")}
            for c in weakest
        ],
        "propagation_table": propagation_table,
        "confidence": confidence,
        "counterfactuals": (counterfactual or {}).get("scenarios") or [],
        "portfolio_impact": portfolio_impact,
        "committee": {
            "event_propagation_map": (event_pack or {}).get("propagation_map"),
            "most_affected": {
                "sectors": (event_pack or {}).get("affected_sectors") or [],
                "companies": (event_pack or {}).get("affected_companies") or ([ticker.upper()] if ticker else []),
            },
            "confidence": (confidence or {}).get("confidence"),
            "alternative_scenarios": (counterfactual or {}).get("scenarios") or [],
        },
        "cio_brief": (
            f"Institutional narrative: {(why_lines[0] if why_lines else 'Causal transmission active')}. "
            f"Confidence {(confidence or {}).get('label')} ({(confidence or {}).get('confidence')}). "
            "Relationships — not isolated events — explain why markets and the portfolio changed."
        ),
        "writer_blocks": {
            "relationship_diagrams": [
                {"nodes": c.get("path"), "labels": c.get("path_labels")} for c in chains[:8]
            ],
            "propagation_tables": propagation_table,
            "impact_summaries": why_lines,
        },
        "text": "\n".join(why_lines),
    }
