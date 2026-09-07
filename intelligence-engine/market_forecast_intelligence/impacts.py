"""Market → sector leadership cascade for forecast scenarios."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence.schema import (
    ImpactLabel,
    MarketScenario,
    ScenarioType,
    SectorLeadershipImpact,
)
from market_forecast_intelligence.templates import leadership_for

SCENARIO_STANCE: dict[ScenarioType, ImpactLabel] = {
    "Bull": "Positive",
    "Base": "Neutral",
    "Bear": "Negative",
}


def sector_impacts_for(
    market: str,
    scenario: ScenarioType,
    *,
    relationships: list[dict[str, Any]] | None = None,
) -> list[SectorLeadershipImpact]:
    lead = leadership_for(market, scenario)
    stance = SCENARIO_STANCE[scenario]
    rows: list[SectorLeadershipImpact] = []
    for sector in lead.get("leaders") or []:
        refs = [
            f"{r.get('source')}→{r.get('target')}"
            for r in (relationships or [])
            if sector.lower() in str(r.get("source") or "").lower()
            or sector.lower() in str(r.get("target") or "").lower()
        ][:3]
        rows.append(
            SectorLeadershipImpact(
                sector=sector,
                impact="Strong Positive" if scenario == "Bull" else stance,
                role="leader",
                rationale=f"{scenario} path favours {sector} leadership",
                relationship_refs=refs or ["MKRI_KRIG"],
            )
        )
    for sector in lead.get("weak") or []:
        rows.append(
            SectorLeadershipImpact(
                sector=sector,
                impact="Strong Negative" if scenario == "Bear" else (
                    "Negative" if scenario == "Bull" else "Neutral"
                ),
                role="weak",
                rationale=f"{scenario} path leaves {sector} relatively weaker",
                relationship_refs=["MKRI_KRIG"],
            )
        )
    return rows


def impact_matrices(
    scenarios: list[MarketScenario],
) -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    leadership: dict[str, list[str]] = {"Bull": [], "Base": [], "Bear": []}
    matrix: dict[str, dict[str, str]] = {}
    for sc in scenarios:
        leadership[sc.scenario] = list(sc.sector_leadership)
        for imp in sc.sector_impacts:
            matrix.setdefault(imp.sector, {})[sc.scenario] = imp.impact
    return leadership, matrix
