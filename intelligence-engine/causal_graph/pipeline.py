"""CIG analyse pipeline — company / event / graph causal packs."""

from __future__ import annotations

from typing import Any

from causal_graph.company_links.seed import COMPANY_LINKS
from causal_graph.confidence.model import causal_confidence
from causal_graph.evidence.attach import evidence_pack
from causal_graph.graph.store import edges as all_edges
from causal_graph.graph.store import graph_snapshot, resolve_company
from causal_graph.propagation.engine import list_events, propagate_event
from causal_graph.reports.build import build_report
from causal_graph.scenarios.counterfactual import counterfactuals
from causal_graph.schema import CIG_VERSION, PRIMARY_QUESTION
from causal_graph.sector_links.models import SECTOR_MODELS, model_for_sector
from causal_graph.transmission.chains import transmission_from, transmissions_for_company

# Historical learning seed — previous event → observed impact
HISTORICAL_LEARNING: list[dict[str, Any]] = [
    {
        "previous_event": "repo_rate_cut",
        "observed_impact": "Credit growth and housing-linked materials improved with a 2–4 quarter lag",
        "duration_quarters": 4,
        "magnitude": "moderate",
        "recovery": "sector rotation into banks/housing",
        "false_signals": ["Immediate NIM collapse narratives without deposit repricing lag"],
    },
    {
        "previous_event": "oil_spike",
        "observed_impact": "CPI and bond yields rose; high-duration bank multiples compressed",
        "duration_quarters": 3,
        "magnitude": "high",
        "recovery": "partial as supply normalises",
        "false_signals": ["One-day equity moves attributed solely to crude without yield confirmation"],
    },
    {
        "previous_event": "rupee_weakness",
        "observed_impact": "Imported inflation pressure on FMCG; IT translation benefit",
        "duration_quarters": 2,
        "magnitude": "moderate",
        "recovery": "mixed by sector",
        "false_signals": ["Treating INR moves as pure IT alpha without US demand context"],
    },
]


def _portfolio_impact(ticker: str | None, event_pack: dict[str, Any] | None) -> dict[str, Any]:
    """Soft estimate of sector/factor/macro transmission risk for a name or event."""
    sectors = list((event_pack or {}).get("affected_sectors") or [])
    t = (ticker or "").upper()
    links = COMPANY_LINKS.get(t) or {}
    sector = links.get("sector")
    if sector and f"sector_{sector.split('_')[0]}" not in sectors:
        # map it_services → sector_it etc.
        alias = {
            "banks": "sector_banks",
            "it_services": "sector_it",
            "metals": "sector_metals",
            "fmcg": "sector_fmcg",
        }.get(sector)
        if alias:
            sectors = list(dict.fromkeys(sectors + [alias]))
    factor_exposure = {
        "rates": 0.8 if sector == "banks" else 0.35,
        "usd": 0.85 if sector == "it_services" else 0.3,
        "oil": 0.55 if sector in {"fmcg", "banks"} else 0.4,
        "china": 0.85 if sector == "metals" else 0.25,
        "inflation": 0.7 if sector == "fmcg" else 0.45,
    }
    return {
        "ticker": t or None,
        "sector_exposure": sectors or ([f"sector_{sector}"] if sector else []),
        "factor_exposure": factor_exposure,
        "macro_sensitivity": {
            "repo_rate": 0.8 if sector == "banks" else 0.4,
            "oil": factor_exposure["oil"],
            "usd": factor_exposure["usd"],
            "us_10y": 0.65 if sector in {"banks", "it_services"} else 0.4,
        },
        "transmission_risk": round(
            max(factor_exposure.values()) if factor_exposure else 0.4,
            3,
        ),
        "rule": "Portfolio impact is transmission exposure — not a buy/sell recommendation",
        "never_recommendation": True,
    }


def analyse_company(ticker: str, *, event: str | None = None) -> dict[str, Any]:
    t = resolve_company(ticker)
    if not t:
        return {
            "found": False,
            "ticker": (ticker or "").upper(),
            "cig_version": CIG_VERSION,
            "primary_question": PRIMARY_QUESTION,
        }
    company = transmissions_for_company(t)
    event_pack: dict[str, Any] = {}
    if event:
        event_pack = propagate_event(event)
    else:
        # Default explanatory event lens by sector
        sector = company.get("sector")
        default_event = {
            "banks": "repo_rate_cut",
            "it_services": "usd_strength",
            "metals": "china_slowdown",
            "fmcg": "rupee_weakness",
        }.get(sector or "", "oil_spike")
        event_pack = propagate_event(default_event)

    # Edges touching company or its upstream
    relevant_ids = {t, *list(company.get("upstream_drivers") or [])}
    rel_edges = [
        e
        for e in all_edges()
        if str(e.get("source")) in relevant_ids or str(e.get("target")) in relevant_ids
    ]
    conf = causal_confidence(rel_edges, company.get("chains"))
    evid = evidence_pack(rel_edges)
    cf = counterfactuals(event_pack.get("event"), ticker=t)
    port = _portfolio_impact(t, event_pack)
    hist = [h for h in HISTORICAL_LEARNING if h.get("previous_event") == event_pack.get("event")]
    report = build_report(
        ticker=t,
        company_pack=company,
        event_pack=event_pack,
        confidence=conf,
        counterfactual=cf,
        portfolio_impact=port,
    )
    return {
        "found": True,
        "ticker": t,
        "cig_version": CIG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "sector": company.get("sector"),
        "upstream_drivers": company.get("upstream_drivers"),
        "sector_model": company.get("sector_model"),
        "chains": company.get("chains"),
        "primary_effects": company.get("primary_effects"),
        "secondary_effects": company.get("secondary_effects"),
        "third_order_effects": company.get("third_order_effects"),
        "event": event_pack,
        "confidence": conf,
        "evidence": evid,
        "counterfactuals": cf,
        "portfolio_impact": port,
        "historical_learning": hist or HISTORICAL_LEARNING[:2],
        "report": report,
        "does_not_replace_company_analysis": True,
        "never_recommendation": True,
        "not_an_engine_redesign": True,
    }


def analyse_event(event: str) -> dict[str, Any]:
    pack = propagate_event(event)
    if not pack.get("found"):
        return {"found": False, "cig_version": CIG_VERSION, **pack}
    # Collect edges along chains
    edge_rows = []
    for c in pack.get("chains") or []:
        edge_rows.extend(c.get("edges") or [])
    conf = causal_confidence(edge_rows, pack.get("chains"))
    evid = evidence_pack(edge_rows)
    cf = counterfactuals(pack.get("event"))
    port = _portfolio_impact(None, pack)
    report = build_report(event_pack=pack, confidence=conf, counterfactual=cf, portfolio_impact=port)
    return {
        "found": True,
        "cig_version": CIG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        **pack,
        "confidence": conf,
        "evidence": evid,
        "counterfactuals": cf,
        "portfolio_impact": port,
        "historical_learning": [
            h for h in HISTORICAL_LEARNING if h.get("previous_event") == pack.get("event")
        ]
        or HISTORICAL_LEARNING[:1],
        "report": report,
        "never_recommendation": True,
        "not_an_engine_redesign": True,
    }


def analyse_query(
    *,
    ticker: str | None = None,
    event: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    """POST /analyse entry — company, event, or both."""
    q = (question or "").lower()
    inferred_event = event
    if not inferred_event:
        if "rate cut" in q or "repo" in q and "cut" in q:
            inferred_event = "repo_rate_cut"
        elif "oil" in q or "crude" in q:
            inferred_event = "oil_spike" if ("rise" in q or "up" in q or "spike" in q) else "oil_decline"
        elif "rupee" in q or "inr" in q:
            inferred_event = "rupee_weakness"
        elif "10" in q and "yield" in q or "us 10" in q:
            inferred_event = "us_10y_rise"
        elif "china" in q:
            inferred_event = "china_slowdown"
        elif "usd" in q or "dollar" in q:
            inferred_event = "usd_strength"

    if ticker:
        out = analyse_company(ticker, event=inferred_event)
        out["question"] = question
        return out
    if inferred_event:
        out = analyse_event(inferred_event)
        out["question"] = question
        return out
    # Graph overview analyse
    snap = graph_snapshot()
    sample_chains = transmission_from("oil", max_chains=8)
    return {
        "found": True,
        "cig_version": CIG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "graph": {"node_count": snap["node_count"], "edge_count": snap["edge_count"]},
        "sample_transmission": sample_chains,
        "available_events": list_events(),
        "sectors_modelled": list(SECTOR_MODELS.keys()),
        "never_recommendation": True,
    }


def heatmap(edges: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = edges if edges is not None else all_edges()
    return sorted(
        [
            {
                "source": e.get("source"),
                "target": e.get("target"),
                "strength": e.get("strength"),
                "confidence": e.get("confidence"),
                "evidence_years": e.get("evidence_years"),
                "score": round(float(e.get("strength") or 0) * float(e.get("confidence") or 0), 3),
            }
            for e in rows
        ],
        key=lambda r: -float(r["score"]),
    )


def sector_explanation(sector: str) -> dict[str, Any]:
    model = model_for_sector(sector)
    if not model:
        return {"found": False, "sector": sector}
    start = (model.get("chain") or ["demand"])[0]
    chains = transmission_from(start, max_depth=4, max_chains=10)
    return {
        "found": True,
        "sector": model.get("sector"),
        "narrative": model.get("narrative"),
        "chain": model.get("chain"),
        "transmission_effects": chains,
        "rule": "Every sector explanation includes transmission effects",
    }
