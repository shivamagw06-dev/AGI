"""Deterministic institutional scenario narratives — evidence-linked, not predictions."""

from __future__ import annotations

from typing import Any

from institutional_scenario_intelligence.schema import ScenarioDrivers, ScenarioType

# Company-specific narrative overlays (Infosys success path from sprint brief)
COMPANY_NARRATIVES: dict[str, dict[str, list[str]]] = {
    "INFY": {
        "Bull": [
            "Enterprise AI spending accelerates.",
            "Large-deal pipeline converts.",
            "Operating margins recover.",
            "USD remains supportive.",
        ],
        "Base": [
            "Revenue grows near guidance.",
            "Margins remain stable.",
            "Valuation stays around long-term average.",
        ],
        "Bear": [
            "US enterprise spending weakens.",
            "Pricing pressure continues.",
            "Margins compress.",
            "Hiring slows.",
        ],
    },
    "HDFCBANK": {
        "Bull": [
            "RBI easing transmits into loan growth.",
            "Liability franchise supports volume expansion.",
            "Asset quality remains contained.",
        ],
        "Base": [
            "Loan growth tracks system with stable NIMs.",
            "Deposit franchise holds share.",
            "Credit costs stay within guidance band.",
        ],
        "Bear": [
            "NIM compression outpaces volume gains.",
            "Unsecured stress rises.",
            "Deposit competition intensifies.",
        ],
    },
    "TCS": {
        "Bull": [
            "Large-deal TCV re-accelerates.",
            "AI services mix expands.",
            "Margins defend at franchise levels.",
        ],
        "Base": [
            "Growth tracks sector mid-cycle.",
            "Margins remain resilient.",
            "Competitive position stays stable.",
        ],
        "Bear": [
            "Discretionary IT budgets stay cautious.",
            "Deal conversion delays persist.",
            "Pricing pressure weighs on margins.",
        ],
    },
    "RELIANCE": {
        "Bull": [
            "Energy spreads improve.",
            "Retail / digital cash generation strengthens.",
            "Capex cycle yields operating leverage.",
        ],
        "Base": [
            "Segment mix delivers steady conglomerate earnings.",
            "Balance sheet flexibility preserved.",
        ],
        "Bear": [
            "Crude / refining volatility pressures earnings.",
            "Consumer demand softens.",
            "Capex intensity delays free cash flow.",
        ],
    },
}

SECTOR_NARRATIVES: dict[str, dict[str, list[str]]] = {
    "information_technology": {
        "Bull": [
            "US tech spending re-accelerates.",
            "AI budgets convert from pilots to production.",
            "Sector margins stabilise with utilisation recovery.",
        ],
        "Base": [
            "Demand remains mixed across verticals.",
            "Growth near long-term mid-cycle.",
            "Valuation holds a quality premium.",
        ],
        "Bear": [
            "Weak US demand persists.",
            "Strong USD masks weak constant-currency growth.",
            "Margin pressure continues.",
        ],
    },
    "financials": {
        "Bull": [
            "Rate-cut cycle lifts housing and auto finance.",
            "Private banks outperform on volume.",
            "Credit costs stay benign.",
        ],
        "Base": [
            "Growth and NIM trade off in an easing path.",
            "Credit cycle remains orderly.",
        ],
        "Bear": [
            "NIM compression dominates.",
            "Credit costs rise in unsecured books.",
            "Liquidity tightens unexpectedly.",
        ],
    },
}

MARKET_NARRATIVES: dict[str, list[str]] = {
    "Bull": [
        "Liquidity remains abundant.",
        "Breadth improves beyond leadership concentration.",
        "Valuation premium is supported by earnings delivery.",
    ],
    "Base": [
        "NIFTY consolidates with mixed breadth.",
        "Valuation stays elevated vs long-term median.",
        "Volatility remains contained.",
    ],
    "Bear": [
        "Liquidity withdraws.",
        "Valuation compresses.",
        "Risk appetite fades as global shocks transmit.",
    ],
}

MACRO_NARRATIVES: dict[str, list[str]] = {
    "Bull": [
        "Inflation continues to moderate.",
        "RBI delivers a clean easing path.",
        "GDP growth remains resilient.",
    ],
    "Base": [
        "RBI stays data-dependent with gradual easing optionality.",
        "Growth moderates without a hard landing.",
        "INR stays manageable for exporters.",
    ],
    "Bear": [
        "Inflation re-accelerates.",
        "Easing path is delayed or reversed.",
        "Currency pressure complicates policy.",
    ],
}


def drivers_for(scenario_type: ScenarioType, *, scope: str, entity: str) -> ScenarioDrivers:
    t = scenario_type.value
    if scope == "company":
        if t == "Bull":
            return ScenarioDrivers(
                revenue="Accelerating growth from deal conversion / AI demand",
                margins="Recovery as utilisation and pricing improve",
                cash_flow="FCF expands with operating leverage",
                valuation="Premium sustained if growth re-rates",
                growth="Above mid-cycle",
                macro="Supportive USD / policy backdrop where relevant",
                sector="Sector demand improves",
                competition="Share gains vs peers on large deals",
            )
        if t == "Bear":
            return ScenarioDrivers(
                revenue="Growth slows on weak enterprise spending",
                margins="Compression from pricing / utilisation pressure",
                cash_flow="FCF softens with lower conversion",
                valuation="Multiple compresses toward trough history",
                growth="Below mid-cycle",
                macro="Adverse demand or FX backdrop",
                sector="Sector under pressure",
                competition="Share / pricing pressure from peers",
            )
        return ScenarioDrivers(
            revenue="Near guidance / mid-cycle growth",
            margins="Stable around recent run-rate",
            cash_flow="Steady conversion",
            valuation="Around long-term average",
            growth="In-line with guidance",
            macro="Neutral to mildly supportive",
            sector="Mixed but orderly",
            competition="Stable competitive set",
        )
    if scope == "sector":
        if t == "Bull":
            return ScenarioDrivers(
                growth="Sector demand re-accelerates",
                margins="Margin defence succeeds",
                valuation="Quality premium expands",
                sector="Leadership and peers both improve",
                macro="Supportive global / domestic demand",
            )
        if t == "Bear":
            return ScenarioDrivers(
                growth="Prolonged demand air-pocket",
                margins="Sector-wide pressure",
                valuation="De-rating",
                sector="Under pressure",
                macro="Global slowdown transmits",
            )
        return ScenarioDrivers(
            growth="Mid-cycle",
            margins="Stable",
            valuation="Holds quality premium",
            sector="Mixed verticals",
            macro="Data-dependent",
        )
    if scope == "market":
        if t == "Bull":
            return ScenarioDrivers(valuation="Premium supported", growth="Earnings delivery", macro="Liquidity supportive")
        if t == "Bear":
            return ScenarioDrivers(valuation="Compression", growth="Earnings disappointment", macro="Liquidity withdraws")
        return ScenarioDrivers(valuation="Elevated but stable", growth="Mixed breadth", macro="Contained volatility")
    # macro
    if t == "Bull":
        return ScenarioDrivers(macro="Clean easing + resilient GDP", growth="Above trend domestic demand")
    if t == "Bear":
        return ScenarioDrivers(macro="Inflation / FX shock delays easing", growth="Harder landing risk")
    return ScenarioDrivers(macro="Gradual data-dependent easing", growth="Moderating but resilient")


def narratives_for(scope: str, entity: str, scenario_type: ScenarioType) -> list[str]:
    t = scenario_type.value
    if scope == "company":
        overlay = COMPANY_NARRATIVES.get(entity.upper()) or {}
        if t in overlay:
            return list(overlay[t])
        return list(COMPANY_NARRATIVES["INFY"][t])
    if scope == "sector":
        key = entity.lower().replace(" ", "_")
        overlay = SECTOR_NARRATIVES.get(key) or SECTOR_NARRATIVES["information_technology"]
        return list(overlay[t])
    if scope == "market":
        return list(MARKET_NARRATIVES[t])
    return list(MACRO_NARRATIVES[t])


def qualitative_confidence(bundle: dict[str, Any], scenario_type: ScenarioType) -> str:
    score = float(((bundle.get("completeness") or {}).get("score")) or 0)
    evidence_n = len(bundle.get("supporting_evidence") or [])
    if score >= 0.7 and evidence_n >= 3:
        return "High" if scenario_type == ScenarioType.BASE else "Medium"
    if score >= 0.45:
        return "Medium"
    return "Low"
