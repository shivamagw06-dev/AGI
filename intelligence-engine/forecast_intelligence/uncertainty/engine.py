"""Uncertainty engine — knowns, known unknowns, unknown unknowns; never hide uncertainty."""

from __future__ import annotations

from typing import Any


def uncertainty_assessment(profile: dict[str, Any], *, catalysts: dict[str, Any] | None = None) -> dict[str, Any]:
    knowns = [
        f"Sector: {profile.get('sector')}",
        f"Key drivers: {', '.join(profile.get('key_drivers') or [])}",
        "Scenario set always includes bull/base/bear/stress/recovery",
    ]
    known_unknowns = [
        "Exact timing of policy / macro catalysts",
        "Magnitude of transmission from macro shocks into company financials",
        "Management execution variance versus guidance",
    ]
    unknown_unknowns = [
        "Unmodelled regulatory interventions",
        "Geopolitical shocks outside current catalyst set",
        "Structural breaks not present in historical analogues",
    ]
    unknown_cats = list((catalysts or {}).get("by_kind", {}).get("unknown") or [])
    if unknown_cats:
        known_unknowns.append(
            "Unknown-kind catalysts: " + ", ".join(c.get("label") or c.get("id") for c in unknown_cats)
        )
    weak = [
        "Sparse real-time catalyst confirmation until next print",
        "Historical analogues are imperfect matches",
    ]
    conflicting = []
    market = profile.get("market_expects") or {}
    agib = profile.get("agib_base") or {}
    if market.get("narrative") and agib.get("narrative") and market.get("narrative") != agib.get("narrative"):
        conflicting.append("Market narrative vs AGIB base narrative diverge in emphasis")
    # Higher unknown catalyst count → higher uncertainty
    u = 0.35 + 0.05 * len(unknown_cats) + 0.03 * len(conflicting)
    u = min(0.85, round(u, 3))
    return {
        "knowns": knowns,
        "known_unknowns": known_unknowns,
        "unknown_unknowns": unknown_unknowns,
        "weak_evidence": weak,
        "conflicting_evidence": conflicting,
        "uncertainty_score": u,
        "explicitly_disclosed": True,
        "rule": "Never hide uncertainty — no deterministic forecasts",
    }
