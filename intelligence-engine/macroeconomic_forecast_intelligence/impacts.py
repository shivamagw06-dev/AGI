"""Deterministic sector/company impact matrix from MRI relationships + scenario stance."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence.schema import (
    CompanyImpact,
    ImpactLabel,
    MacroScenario,
    ScenarioType,
    SectorImpact,
)

# Canonical sectors for the matrix
SECTORS: tuple[str, ...] = (
    "Banks",
    "IT Services",
    "FMCG",
    "Auto",
    "Capital Goods",
    "Realty",
    "Oil & Gas",
    "Metals",
)

# Fallback transmission when MRI empty — still evidence-linked to catalog logic
SECTOR_STANCE: dict[str, dict[ScenarioType, tuple[ImpactLabel, str]]] = {
    "Banks": {
        "Bull": ("Positive", "Easing + credit acceleration historically supports private banks"),
        "Base": ("Neutral", "NIM/volume trade-off under cautious policy"),
        "Bear": ("Negative", "Delayed cuts + slower credit growth pressure volumes"),
    },
    "IT Services": {
        "Bull": ("Neutral", "Domestic easing helps; global demand still primary driver"),
        "Base": ("Neutral", "USDINR stable; demand mixed"),
        "Bear": ("Positive", "INR weakness historically supports exporter revenues"),
    },
    "FMCG": {
        "Bull": ("Positive", "Lower inflation supports real consumption"),
        "Base": ("Neutral", "Volume stable near-target inflation"),
        "Bear": ("Negative", "Margin pressure from re-accelerating CPI/WPI"),
    },
    "Auto": {
        "Bull": ("Positive", "Lower rates + credit growth lift vehicle financing"),
        "Base": ("Moderate", "Steady demand without strong impulse"),
        "Bear": ("Negative", "Weak consumption and tighter financing"),
    },
    "Capital Goods": {
        "Bull": ("Strong Positive", "Private + government capex improves order books"),
        "Base": ("Moderate", "Public capex carries; private cautious"),
        "Bear": ("Negative", "Capex deferral under growth/inflation stress"),
    },
    "Realty": {
        "Bull": ("Positive", "Rate-sensitive housing demand improves with easing"),
        "Base": ("Neutral", "Affordability stable under hold/cautious stance"),
        "Bear": ("Negative", "Higher-for-longer rates cool transactions"),
    },
    "Oil & Gas": {
        "Bull": ("Neutral", "Stable crude supportive; less shock premium"),
        "Base": ("Neutral", "Range-bound commodity assumptions"),
        "Bear": ("Positive", "Higher oil lifts upstream realizations (downstream mixed)"),
    },
    "Metals": {
        "Bull": ("Positive", "Global growth recovery lifts demand"),
        "Base": ("Neutral", "Demand tracks modest global growth"),
        "Bear": ("Negative", "Global slowdown + cost inflation"),
    },
}

COMPANY_MAP: dict[str, list[tuple[str, str]]] = {
    # sector → (ticker, note)
    "Banks": [
        ("HDFCBANK", "Private bank credit / NIM transmission"),
        ("ICICIBANK", "Private bank volume sensitivity"),
        ("AXISBANK", "Private bank credit growth"),
        ("SBIN", "PSU bank credit / policy transmission"),
    ],
    "IT Services": [
        ("INFY", "USDINR / global demand sensitivity"),
        ("TCS", "Exporter FX + discretionary IT spend"),
        ("WIPRO", "Exporter FX sensitivity"),
    ],
    "FMCG": [
        ("HINDUNILVR", "Volume / margin under CPI"),
        ("ITC", "FMCG mix cost inflation"),
        ("NESTLEIND", "Input cost / volume"),
    ],
    "Auto": [
        ("MARUTI", "Rate-sensitive passenger vehicles"),
        ("M&M", "Auto + rural demand"),
        ("TATAMOTORS", "CV / PV cyclicality"),
    ],
    "Capital Goods": [
        ("LT", "Infra / capex orders"),
        ("SIEMENS", "Industrial capex"),
    ],
    "Realty": [
        ("DLF", "Housing rate sensitivity"),
        ("GODREJPROP", "Residential demand"),
    ],
}


def _soft_mri_rows() -> list[dict[str, Any]]:
    try:
        from macroeconomic_relationship_intelligence.production import relationships

        pack = relationships(limit=200)
        return list(pack.get("relationships") or [])
    except Exception:
        return []


def _rels_for_target(rows: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    key = target.upper().replace(" ", "")
    out = []
    for r in rows:
        t = str(r.get("target") or "").upper().replace(" ", "")
        if key in t or t in key or target.lower() in str(r.get("target") or "").lower():
            out.append(r)
    return out


def sector_impacts_for(
    scenario: ScenarioType,
    *,
    relationships: list[dict[str, Any]] | None = None,
) -> list[SectorImpact]:
    rows = relationships if relationships is not None else _soft_mri_rows()
    impacts: list[SectorImpact] = []
    for sector in SECTORS:
        label, rationale = SECTOR_STANCE[sector][scenario]
        rels = _rels_for_target(rows, sector)
        # Refine Banks impact if easing/tightening from repo relationships
        if sector == "Banks" and scenario == "Bull" and any(
            "Repo" in str(r.get("source")) for r in rels
        ):
            label = "Positive"
        refs = [str(r.get("relationship_id") or f"{r.get('source')}->{r.get('target')}") for r in rels[:3]]
        if rels:
            rationale = f"{rationale} (MRI: {rels[0].get('relationship')})"
        impacts.append(
            SectorImpact(
                sector=sector,
                impact=label,
                rationale=rationale,
                relationship_refs=refs,
            )
        )
    return impacts


def company_impacts_for(
    scenario: ScenarioType,
    sector_impacts: list[SectorImpact],
    *,
    relationships: list[dict[str, Any]] | None = None,
) -> list[CompanyImpact]:
    rows = relationships if relationships is not None else _soft_mri_rows()
    sector_label = {s.sector: s.impact for s in sector_impacts}
    out: list[CompanyImpact] = []
    for sector, companies in COMPANY_MAP.items():
        impact = sector_label.get(sector, "Neutral")
        for ticker, note in companies:
            rels = _rels_for_target(rows, ticker)
            if not rels:
                rels = _rels_for_target(rows, sector)
            chain = ["Repo Rate", sector, ticker, "Credit Growth"] if sector == "Banks" else [
                "Macro Regime",
                sector,
                ticker,
            ]
            if rels and rels[0].get("chain"):
                chain = list(rels[0]["chain"]) + [ticker]
            rationale = note
            if scenario == "Bull" and sector == "Banks":
                rationale = "Repo ↓ → Banks → credit growth ↑ (historical transmission)"
            elif scenario == "Bear" and sector == "IT Services":
                rationale = "INR weakness can support exporter revenues even as domestic demand softens"
            refs = [
                str(r.get("relationship_id") or f"{r.get('source')}->{r.get('target')}")
                for r in rels[:3]
            ]
            out.append(
                CompanyImpact(
                    ticker=ticker,
                    sector=sector,
                    impact=impact,  # type: ignore[arg-type]
                    transmission=chain,
                    rationale=rationale,
                    relationship_refs=refs,
                )
            )
    return out


def impact_matrices(scenarios: list[MacroScenario]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    sector_matrix: dict[str, dict[str, str]] = {s: {} for s in SECTORS}
    company_matrix: dict[str, dict[str, str]] = {}
    for sc in scenarios:
        for si in sc.sector_impacts:
            sector_matrix.setdefault(si.sector, {})[sc.scenario] = si.impact
        for ci in sc.company_impacts:
            company_matrix.setdefault(ci.ticker, {})[sc.scenario] = ci.impact
    return sector_matrix, company_matrix
