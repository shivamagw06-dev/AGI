"""Seeded actual outcomes for deterministic FVL validation.

No live Yahoo / NSE / BSE calls. Outcomes are AGI-owned fixture knowledge
representing institutional post-facto observations (earnings, sector, market, macro).
"""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import ActualOutcome

# Company actuals — post-forecast institutional observations
_COMPANY_ACTUALS: dict[str, dict[str, Any]] = {
    "INFY": {
        "realized_scenario": "Base",
        "growth_direction": "up",
        "margin_direction": "stable",
        "catalysts_materialized": [
            "Updated Management Guidance",
            "Large Deal Wins",
        ],
        "timing_realized": "on_time",
        "metrics": {
            "revenue_growth_pct": 6.5,
            "ebitda_margin_pct": 21.2,
            "pat_growth_pct": 5.0,
            "guidance_tone": "cautiously_constructive",
        },
        "evidence": [
            {"type": "earnings", "label": "Q results vs Base case"},
            {"type": "guidance", "label": "Management commentary constructive"},
            {"type": "corporate_action", "label": "No material M&A surprise"},
        ],
        "notes": "Revenue trajectory aligned with Base; guidance more informative than valuation moves.",
    },
    "TCS": {
        "realized_scenario": "Base",
        "growth_direction": "up",
        "margin_direction": "up",
        "catalysts_materialized": ["Deal Pipeline Conversion"],
        "timing_realized": "on_time",
        "metrics": {"revenue_growth_pct": 5.8, "ebitda_margin_pct": 25.0, "pat_growth_pct": 6.2},
        "evidence": [{"type": "earnings", "label": "Steady growth, margin discipline"}],
        "notes": "Base case realized with modest margin expansion.",
    },
    "HDFCBANK": {
        "realized_scenario": "Bull",
        "growth_direction": "up",
        "margin_direction": "up",
        "catalysts_materialized": ["Loan Growth Acceleration", "Asset Quality Stability"],
        "timing_realized": "early",
        "metrics": {"revenue_growth_pct": 12.0, "nim_bps": 5, "pat_growth_pct": 14.0},
        "evidence": [
            {"type": "earnings", "label": "Loan growth above Base"},
            {"type": "asset_quality", "label": "Slippages contained"},
        ],
        "notes": "Bull path more frequent than modal Base probability implied.",
    },
    "RELIANCE": {
        "realized_scenario": "Bear",
        "growth_direction": "down",
        "margin_direction": "down",
        "catalysts_materialized": ["Commodity Margin Compression"],
        "timing_realized": "on_time",
        "metrics": {"revenue_growth_pct": 1.0, "ebitda_margin_pct": -1.5, "pat_growth_pct": -4.0},
        "evidence": [{"type": "earnings", "label": "Downstream margin pressure"}],
        "notes": "Bear catalysts dominated; growth systematically weaker than Base.",
    },
    "ITC": {
        "realized_scenario": "Base",
        "growth_direction": "stable",
        "margin_direction": "up",
        "catalysts_materialized": ["FMCG Mix Improvement"],
        "timing_realized": "late",
        "metrics": {"revenue_growth_pct": 4.0, "ebitda_margin_pct": 0.8, "pat_growth_pct": 5.5},
        "evidence": [{"type": "earnings", "label": "Stable cigarettes; FMCG mix slow"}],
        "notes": "Timing lagged; margins better than growth narrative implied.",
    },
}

_SECTOR_ACTUALS: dict[str, dict[str, Any]] = {
    "INFORMATION_TECHNOLOGY": {
        "realized_scenario": "Base",
        "growth_direction": "up",
        "margin_direction": "stable",
        "catalysts_materialized": ["Deal Wins", "Discretionary Spend Stabilisation"],
        "timing_realized": "on_time",
        "metrics": {"sector_growth_pct": 6.0, "relative_performance": "inline", "demand": "stable_to_up"},
        "evidence": [{"type": "sector", "label": "IT demand stable; relative performance inline"}],
        "notes": "Sector Base realized; relative performance matched modal case.",
    },
    "BANKS": {
        "realized_scenario": "Bull",
        "growth_direction": "up",
        "margin_direction": "up",
        "catalysts_materialized": ["Credit Growth", "Stable Asset Quality"],
        "timing_realized": "on_time",
        "metrics": {"sector_growth_pct": 11.0, "relative_performance": "outperform", "demand": "up"},
        "evidence": [{"type": "sector", "label": "Credit impulse stronger than Base"}],
        "notes": "Bull overweight in banks relative to prior probabilities.",
    },
}

_MARKET_ACTUAL: dict[str, Any] = {
    "realized_scenario": "Base",
    "growth_direction": "up",
    "margin_direction": "stable",
    "catalysts_materialized": ["Breadth Improvement", "Volatility Compression"],
    "timing_realized": "on_time",
    "metrics": {
        "index_return_pct": 8.0,
        "valuation_change": "mild_expansion",
        "breadth": "improving",
        "volatility": "lower",
    },
    "evidence": [
        {"type": "market", "label": "Index returns within Base band"},
        {"type": "market", "label": "Volatility declined vs forecast window"},
    ],
    "notes": "Market Base path; valuation changes less predictive than breadth.",
}

_MACRO_ACTUAL: dict[str, Any] = {
    "realized_scenario": "Base",
    "growth_direction": "stable",
    "margin_direction": "stable",
    "catalysts_materialized": ["RBI Hold", "Inflation Moderation"],
    "timing_realized": "on_time",
    "metrics": {
        "rbi_decision": "hold",
        "inflation_trend": "moderating",
        "gdp_growth": "stable",
        "currency": "stable",
        "bond_yields": "range_bound",
    },
    "evidence": [
        {"type": "macro", "label": "RBI decision matched Base"},
        {"type": "macro", "label": "Inflation moderated as expected"},
    ],
    "notes": "Macro Base correct; bond-yield catalysts underweighted historically.",
}


def _build(payload: dict[str, Any]) -> ActualOutcome:
    return ActualOutcome(
        realized_scenario=str(payload.get("realized_scenario") or "Unknown"),
        growth_direction=str(payload.get("growth_direction") or "stable"),
        margin_direction=str(payload.get("margin_direction") or "stable"),
        catalysts_materialized=list(payload.get("catalysts_materialized") or []),
        timing_realized=str(payload.get("timing_realized") or "unknown"),
        evidence=list(payload.get("evidence") or []),
        metrics=dict(payload.get("metrics") or {}),
        source="agi_seeded_outcome",
        notes=str(payload.get("notes") or ""),
    )


def resolve_actual(
    *,
    entity: str,
    scope: str = "company",
    override: dict[str, Any] | None = None,
) -> ActualOutcome | None:
    """Resolve actual outcome from AGI-owned seeds (or explicit override). No live providers."""
    if override:
        return _build(override)

    scope_l = (scope or "company").lower()
    ent = (entity or "").strip().upper().replace(" ", "_").replace("-", "_")

    if scope_l == "company":
        row = _COMPANY_ACTUALS.get(ent)
        return _build(row) if row else None
    if scope_l == "sector":
        row = _SECTOR_ACTUALS.get(ent) or _SECTOR_ACTUALS.get(ent.replace("_", ""))
        # fuzzy: information_technology
        if not row:
            for k, v in _SECTOR_ACTUALS.items():
                if k.replace("_", "") in ent.replace("_", "") or ent.replace("_", "") in k.replace("_", ""):
                    row = v
                    break
        return _build(row) if row else None
    if scope_l == "market":
        return _build(_MARKET_ACTUAL)
    if scope_l == "macro":
        return _build(_MACRO_ACTUAL)
    return None


def available_entities() -> dict[str, list[str]]:
    return {
        "company": sorted(_COMPANY_ACTUALS.keys()),
        "sector": sorted(_SECTOR_ACTUALS.keys()),
        "market": ["NIFTY"],
        "macro": ["INDIA_MACRO"],
    }
