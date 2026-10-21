"""Curated institutional domain / historical-event seeds.

Soft priors only — never invent live facts. Point-in-time via available_from.
Used to fill thin IERE gaps (esp. historical replay) with structured relationships.
"""

from __future__ import annotations

from typing import Any


def historical_event_seeds() -> list[dict[str, Any]]:
    """Company historical event nodes for institutional memory scaffolding."""
    return [
        # INFY timeline — supports Q24 replay depth
        _ev("INFY", "2018-04-01", "Digital services mix expansion disclosed", "guidance", 0.8, "annual_report"),
        _ev("INFY", "2019-04-01", "FY20 guidance framing and large-deal commentary", "guidance", 0.85, "conference_call"),
        _ev("INFY", "2020-03-11", "WHO declares COVID-19 pandemic — IT demand shock risk", "historical_events", 0.95, "news"),
        _ev("INFY", "2020-03-23", "India lockdown begins — delivery / travel disruption risk", "historical_events", 0.95, "news"),
        _ev("INFY", "2020-03-31", "FY20 year-end: available evidence cut-off for March 2020 replay", "historical_events", 0.99, "institutional_documents"),
        _ev("INFY", "2020-07-15", "COVID recovery commentary and digital acceleration", "earnings", 0.8, "conference_call"),
        _ev("INFY", "2021-04-01", "Post-COVID hiring / utilisation rebuild narrative", "management", 0.75, "annual_report"),
        _ev("INFY", "2022-04-01", "Wage inflation / attrition pressure on margins", "financials", 0.8, "conference_call"),
        _ev("INFY", "2023-04-01", "Generative AI client interest vs deal conversion uncertainty", "guidance", 0.7, "investor_presentation"),
        _ev("INFY", "2024-04-01", "AI services strategy and large-deal pipeline focus", "guidance", 0.75, "conference_call"),
        # TCS
        _ev("TCS", "2019-04-01", "Industry-leading margin franchise framing", "financials", 0.8, "annual_report"),
        _ev("TCS", "2020-03-31", "COVID year-end evidence cut-off", "historical_events", 0.95, "institutional_documents"),
        _ev("TCS", "2021-04-01", "Recovery and deal wins commentary", "earnings", 0.75, "conference_call"),
        _ev("TCS", "2023-04-01", "AI and cloud services positioning", "guidance", 0.7, "investor_presentation"),
        # HDFCBANK
        _ev("HDFCBANK", "2018-01-01", "Liability franchise / CASA quality as core thesis pillar", "financials", 0.85, "annual_report"),
        _ev("HDFCBANK", "2020-03-31", "COVID credit-cost uncertainty at year-end", "risks", 0.9, "annual_report"),
        _ev("HDFCBANK", "2022-04-01", "Merger with HDFC Ltd path becomes strategic focus", "corporate_actions", 0.85, "investor_presentation"),
        _ev("HDFCBANK", "2023-07-01", "Merger completion — book / ROE transition watch", "corporate_actions", 0.9, "nse_filings"),
        # RELIANCE
        _ev("RELIANCE", "2019-01-01", "Jio / Retail / O2C SOTP framing established", "segments", 0.85, "annual_report"),
        _ev("RELIANCE", "2020-03-31", "COVID oil / retail demand stress at year-end", "historical_events", 0.9, "annual_report"),
        _ev("RELIANCE", "2022-01-01", "New energy / green transition disclosures", "esg", 0.7, "investor_presentation"),
        # INDIGO / ASIANPAINT / TITAN / MARUTI
        _ev("INDIGO", "2020-03-31", "Aviation demand collapse risk at COVID cut-off", "historical_events", 0.95, "news"),
        _ev("ASIANPAINT", "2020-03-31", "Decorative demand pause risk; crude input sensitivity", "macro_exposure", 0.85, "annual_report"),
        _ev("TITAN", "2020-03-31", "Discretionary retail shutdown risk", "historical_events", 0.85, "news"),
        _ev("MARUTI", "2020-03-31", "Auto demand / supply-chain disruption risk", "historical_events", 0.85, "news"),
    ]


def domain_stub_seeds() -> list[dict[str, Any]]:
    """Lightweight domain stubs (structure only) for key CIO entities."""
    stubs: list[dict[str, Any]] = []
    profiles = {
        "INFY": {
            "competitors": ["TCS", "WIPRO", "HCLTECH", "TECHM"],
            "macro_exposure": ["USDINR", "US_IT_SPEND", "ENTERPRISE_BUDGETS"],
            "segments": ["Financial Services", "Retail", "Manufacturing", "Energy"],
            "products": ["Digital", "Cloud", "AI Services", "Consulting"],
        },
        "TCS": {
            "competitors": ["INFY", "WIPRO", "HCLTECH", "TECHM"],
            "macro_exposure": ["USDINR", "US_IT_SPEND"],
            "segments": ["BFSI", "Retail", "Communication"],
            "products": ["Cloud", "AI", "Enterprise Applications"],
        },
        "HDFCBANK": {
            "competitors": ["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
            "macro_exposure": ["REPO_RATE", "CREDIT_GROWTH", "LIQUIDITY"],
            "segments": ["Retail Banking", "Wholesale Banking"],
            "products": ["CASA", "Mortgages", "Working Capital"],
            "credit": ["GNPA", "NNPA", "PCR", "CET1"],
        },
        "RELIANCE": {
            "competitors": ["ONGC", "BPCL", "IOCL"],
            "macro_exposure": ["CRUDE_OIL", "USDINR", "REFINING_CRACK"],
            "segments": ["O2C", "Jio", "Retail", "New Energy"],
            "products": ["Fuels", "Petrochemicals", "Telecom", "Retail"],
            "suppliers": ["crude_oil"],
        },
        "INDIGO": {
            "competitors": ["SPICEJET"],
            "macro_exposure": ["ATF", "CRUDE_OIL", "USDINR"],
            "products": ["Passenger airline"],
            "suppliers": ["ATF", "aircraft_leases"],
        },
        "ASIANPAINT": {
            "competitors": ["BERGER", "KANSAINER"],
            "macro_exposure": ["CRUDE_OIL", "TIO2", "RURAL_DEMAND"],
            "products": ["Decorative paints", "Industrial coatings"],
            "suppliers": ["crude_oil", "TiO2"],
        },
    }
    for ticker, domains in profiles.items():
        for domain, items in domains.items():
            for item in items:
                stubs.append(
                    {
                        "entity": ticker,
                        "domain": domain,
                        "counterpart": item,
                        "relationship": f"profile_{domain}",
                        "title": f"{ticker} · {domain}: {item}",
                        "source": "ieri",
                        "confidence": 0.72,
                        "available_from": "2018-01-01",
                        "evidence_strength": 7.0,
                        "kind": "relationship_stub",
                    }
                )
    return stubs


def _ev(
    entity: str,
    available_from: str,
    title: str,
    domain: str,
    confidence: float,
    source: str,
) -> dict[str, Any]:
    return {
        "entity": entity,
        "domain": domain,
        "title": title,
        "paragraph": title,
        "source": source,
        "confidence": confidence,
        "available_from": available_from,
        "timestamp": available_from,
        "relationship": "historical_event",
        "kind": "historical_event",
        "evidence_strength": None,
    }
