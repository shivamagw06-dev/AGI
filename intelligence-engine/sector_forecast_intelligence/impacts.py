"""Sector → company impact cascade + peer sector transmission."""

from __future__ import annotations

from typing import Any

from sector_forecast_intelligence.schema import (
    CompanyImpact,
    ImpactLabel,
    PeerSectorImpact,
    ScenarioType,
)

COMPANY_MAP: dict[str, list[tuple[str, str]]] = {
    "Banking": [
        ("HDFCBANK", "Private bank credit / NIM transmission"),
        ("ICICIBANK", "Private bank volume sensitivity"),
        ("AXISBANK", "Private bank credit growth"),
        ("SBIN", "PSU bank credit / policy transmission"),
    ],
    "IT Services": [
        ("INFY", "USDINR / global demand sensitivity"),
        ("TCS", "Exporter FX + discretionary IT spend"),
        ("HCLTECH", "Digital / AI pipeline"),
        ("WIPRO", "Exporter FX sensitivity"),
    ],
    "FMCG": [
        ("HINDUNILVR", "Volume / margin under CPI"),
        ("ITC", "FMCG mix cost inflation"),
        ("NESTLEIND", "Input cost / volume"),
        ("BRITANNIA", "Volume recovery"),
    ],
    "Auto": [
        ("MARUTI", "Rate-sensitive passenger vehicles"),
        ("M&M", "Auto + rural demand"),
        ("TATAMOTORS", "CV / PV cyclicality"),
        ("BAJAJ-AUTO", "2W demand / exports"),
    ],
    "Capital Goods": [
        ("LT", "Infra / capex orders"),
        ("SIEMENS", "Industrial capex"),
        ("ABB", "Electrification / industrial"),
        ("BHEL", "Power equipment / public capex"),
    ],
    "Pharma": [
        ("SUNPHARMA", "US + India diversified"),
        ("DRREDDY", "US generics / complex"),
        ("CIPLA", "India chronic + exports"),
        ("DIVISLAB", "API / custom synthesis"),
    ],
}

COMPANY_STANCE: dict[ScenarioType, ImpactLabel] = {
    "Bull": "Positive",
    "Base": "Neutral",
    "Bear": "Negative",
}

PEER_TRANSMISSION: dict[str, list[tuple[str, str]]] = {
    "Banking": [
        ("Real Estate", "Credit expansion → housing demand"),
        ("Auto", "Financing availability → vehicle demand"),
        ("NBFC", "Funding / liquidity spillovers"),
    ],
    "IT Services": [
        ("Pharma", "Exporter FX co-movement"),
        ("Exporters", "USDINR transmission"),
    ],
    "FMCG": [
        ("Auto", "Rural demand co-cycle"),
    ],
    "Auto": [
        ("Tyres", "Volume transmission"),
        ("Metals", "Commodity cost co-cycle"),
    ],
    "Capital Goods": [
        ("Cement", "Infra spend co-cycle"),
        ("Engineering", "Order book transmission"),
        ("Metals", "Input cost / demand"),
    ],
    "Pharma": [
        ("IT Services", "Exporter FX co-movement"),
    ],
}


def company_impacts_for(
    sector: str,
    scenario: ScenarioType,
    *,
    relationships: list[dict[str, Any]] | None = None,
) -> list[CompanyImpact]:
    impact = COMPANY_STANCE[scenario]
    rows = COMPANY_MAP.get(sector) or []
    out: list[CompanyImpact] = []
    for ticker, note in rows:
        refs = [
            f"sfi:{sector}:{scenario}:{ticker}",
        ]
        for r in relationships or []:
            tgt = str(r.get("target") or "")
            src = str(r.get("source") or "")
            if ticker.upper() in {tgt.upper(), src.upper()}:
                refs.append(str(r.get("relationship_id") or f"sri:{src}->{tgt}"))
        transmission = [sector, scenario, "Sector Outlook", ticker, note]
        if scenario == "Bull":
            transmission = [sector, "Positive Outlook", ticker, "Higher Order Books / Growth", "Revenue Growth"]
        elif scenario == "Bear":
            transmission = [sector, "Negative Outlook", ticker, "Demand / Margin Pressure", "Earnings Risk"]
        out.append(
            CompanyImpact(
                ticker=ticker,
                sector=sector,
                impact=impact if scenario != "Bull" else ("Strong Positive" if sector == "Capital Goods" else impact),
                transmission=transmission,
                rationale=note,
                relationship_refs=refs[:4],
            )
        )
    return out


def peer_impacts_for(
    sector: str,
    scenario: ScenarioType,
    *,
    relationships: list[dict[str, Any]] | None = None,
) -> list[PeerSectorImpact]:
    impact = COMPANY_STANCE[scenario]
    out: list[PeerSectorImpact] = []
    for peer, rationale in PEER_TRANSMISSION.get(sector) or []:
        refs = [f"sfi:{sector}->{peer}:{scenario}"]
        for r in relationships or []:
            blob = f"{r.get('source')}{r.get('target')}".lower()
            if peer.lower() in blob or sector.lower() in blob:
                refs.append(str(r.get("relationship_id") or "sri"))
        out.append(
            PeerSectorImpact(
                sector=peer,
                impact=impact,
                rationale=rationale,
                relationship_refs=refs[:3],
            )
        )
    return out


def impact_matrices(
    scenarios: list[Any],
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    company: dict[str, dict[str, str]] = {}
    peer: dict[str, dict[str, str]] = {}
    for sc in scenarios:
        for c in sc.company_impacts:
            company.setdefault(c.ticker, {})[sc.scenario] = c.impact
        for p in sc.peer_sector_impacts:
            peer.setdefault(p.sector, {})[sc.scenario] = p.impact
    return company, peer
