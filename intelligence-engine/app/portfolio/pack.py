"""Assemble PortfolioPackage — packaging + orchestration only.

Does not invent returns, risk numbers, or trade instructions.
Holding research is deferred to Equity desk / prior run metadata — never fabricated.
"""

from __future__ import annotations

from typing import Any

from app.portfolio.normalize import MODEL_PORTFOLIOS, build_snapshot, sector_exposure
from app.portfolio.recommend import attach_to_package
from app.schemas.models import (
    PortfolioIngestRequest,
    PortfolioPackage,
    PortfolioRecommendation,
    PortfolioSnapshot,
    ResearchRun,
)

WORKSPACE_TABS = [
    "Overview",
    "Portfolio",
    "Research",
    "Forecast",
    "Risk",
    "Events",
    "Action Center",
    "Timeline",
    "Reports",
    "CIO Summary",
]

COMPONENTS_REUSED = [
    "Intelligence Core",
    "Research Director",
    "Memory (RAG)",
    "Evidence Engine",
    "Confidence Engine",
    "Debate Engine",
    "Citation Engine",
    "Equity Research Desk",
    "CIO Committee",
]


def ingest_to_snapshot(req: PortfolioIngestRequest) -> PortfolioSnapshot:
    return build_snapshot(
        name=req.name,
        client_id=req.client_id,
        source=req.source,
        holdings=req.holdings,
        csv_text=req.csv_text,
        model_id=req.model_id,
    )


def _pct(score_01: float | None) -> int | None:
    if score_01 is None:
        return None
    return max(0, min(100, int(round(float(score_01) * 100))))


def _diversification_01(sectors: dict[str, float]) -> float | None:
    if not sectors:
        return None
    hhi = sum(v * v for v in sectors.values())
    return max(0.0, min(1.0, 1.0 - hhi))


def _research_score(holding_research: list[dict[str, Any]]) -> int | None:
    confs = [int(r["confidence"]) for r in holding_research if isinstance(r.get("confidence"), (int, float))]
    if not confs:
        return None
    return max(0, min(100, int(round(sum(confs) / len(confs)))))


def _health_score(
    research: int | None,
    diversification: int | None,
    coverage_pct: int,
) -> int | None:
    parts: list[int] = [coverage_pct]
    if research is not None:
        parts.append(research)
    if diversification is not None:
        parts.append(diversification)
    if not parts:
        return None
    return max(0, min(100, int(round(sum(parts) / len(parts)))))


def _seed_holding_research(
    snapshot: PortfolioSnapshot,
    prior: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Map holdings to research rows. Never invents confidence or stance."""
    by_symbol = {str(r.get("symbol", "")).upper(): r for r in (prior or []) if r.get("symbol")}
    rows: list[dict[str, Any]] = []
    for h in snapshot.holdings:
        prior_row = by_symbol.get(h.symbol.upper())
        if prior_row and prior_row.get("confidence") is not None:
            rows.append(
                {
                    "symbol": h.symbol,
                    "weight": h.weight,
                    "sector": h.sector,
                    "confidence": int(prior_row["confidence"]),
                    "stance": prior_row.get("stance"),
                    "run_id": prior_row.get("run_id"),
                    "thesis": prior_row.get("thesis"),
                    "missing": False,
                    "note": prior_row.get("note") or "Prior equity research attached via metadata.",
                }
            )
        else:
            rows.append(
                {
                    "symbol": h.symbol,
                    "weight": h.weight,
                    "sector": h.sector,
                    "confidence": None,
                    "stance": None,
                    "run_id": None,
                    "missing": True,
                    "note": "Holding research deferred — Equity desk child run not fabricated.",
                }
            )
    return rows


def _executive_health(
    snapshot: PortfolioSnapshot,
    sectors: dict[str, float],
    holding_research: list[dict[str, Any]],
    recommendations: list[PortfolioRecommendation],
) -> dict[str, Any]:
    researched = sum(1 for r in holding_research if not r.get("missing"))
    strengths: list[str] = []
    weaknesses: list[str] = []
    if researched:
        strengths.append(f"Research coverage on {researched}/{len(holding_research)} holdings.")
    else:
        weaknesses.append("No holding-level research packages attached yet.")
    top = list(sectors.items())[:3]
    if top and top[0][1] >= 0.4:
        weaknesses.append(f"Sector concentration: {top[0][0]} ~{top[0][1] * 100:.0f}% of weight.")
    elif top:
        strengths.append(f"Largest sector {top[0][0]} at ~{top[0][1] * 100:.0f}%.")
    high = [r for r in recommendations if r.priority == "high"]
    if high:
        weaknesses.append(f"{len(high)} high-priority review item(s) in Action Center.")
    return {
        "portfolio_health": "Portfolio Office executive summary — research packaging only; not a performance report.",
        "strengths": strengths or ["Ingestion completed into common Portfolio schema."],
        "weaknesses": weaknesses or ["Insufficient data for deeper weakness scoring."],
        "major_risks": [r.title for r in recommendations if r.priority == "high"][:5]
        or ["Risk metrics withheld pending risk engine inputs."],
        "major_opportunities": [
            "Deepen equity research coverage on uncovered holdings.",
            "Run scenario questions against Macro / Forecast when available.",
        ],
        "sector_concentration": [{"sector": s, "weight": w} for s, w in top],
        "macro_exposure": {
            "status": "withheld",
            "note": "Macro exposure requires Macro Intelligence / holding factor map — not fabricated.",
        },
        "forecast_outlook": {
            "status": "withheld",
            "note": "Forecast Layer not available in this build — outlook withheld.",
        },
        "upcoming_events": {
            "status": "withheld",
            "note": "Corporate calendar not wired — events withheld.",
        },
        "research_priorities": [r.title for r in recommendations][:8],
        "disclaimer": "Never fabricate returns or risk. Recommendations use Review/Research/Monitor only.",
    }


def _monthly_report(
    snapshot: PortfolioSnapshot,
    recommendations: list[PortfolioRecommendation],
    holding_research: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "period": "month_to_date",
        "as_of": snapshot.as_of.isoformat() if snapshot.as_of else None,
        "executive_summary": (
            f"Portfolio '{snapshot.name}' with {len(snapshot.holdings)} holdings. "
            "Changes vs prior period require stored timeline baselines — not invented."
        ),
        "portfolio_changes": {"status": "withheld", "note": "Needs prior snapshot comparison."},
        "forecast_changes": {"status": "withheld", "note": "Forecast Layer unavailable."},
        "risk_changes": {"status": "withheld", "note": "Risk engine inputs unavailable."},
        "sector_changes": {"status": "withheld", "note": "Needs prior sector baseline."},
        "research_completed": [
            {"symbol": r.get("symbol"), "run_id": r.get("run_id"), "stance": r.get("stance")}
            for r in holding_research
            if not r.get("missing")
        ],
        "research_outstanding": [r.get("symbol") for r in holding_research if r.get("missing")],
        "watchlist_changes": {
            "status": "withheld",
            "note": "Watchlist Intelligence not wired into this package.",
        },
        "upcoming_events": {"status": "withheld"},
        "recommendations": [r.model_dump() for r in recommendations],
    }


def _timeline_seed(
    snapshot: PortfolioSnapshot,
    health: int | None,
    research: int | None,
) -> list[dict[str, Any]]:
    return [
        {
            "ts": snapshot.as_of.isoformat() if snapshot.as_of else None,
            "label": "ingestion",
            "portfolio_health": health,
            "research_score": research,
            "risk_score": None,
            "forecast_score": None,
            "note": "Baseline timeline point at ingestion. Prior periods require stored history.",
            "compare": {
                "last_week": "withheld",
                "last_month": "withheld",
                "last_quarter": "withheld",
                "last_year": "withheld",
            },
        }
    ]


def _scenario_scaffold() -> dict[str, Any]:
    return {
        "status": "scaffold",
        "allowed_questions": [
            "What happens if oil rises 20%?",
            "What happens if RBI cuts rates?",
            "What happens if the IT sector falls?",
            "What happens if inflation increases?",
            "What happens if I reduce Banking exposure?",
        ],
        "policy": (
            "Scenarios must reuse Forecast Layer + Macro Intelligence + Portfolio Intelligence. "
            "Never invent scenario outcomes. Explain assumptions. Withhold if engines unavailable."
        ),
        "engines": {
            "forecast_layer": "unavailable_in_this_build",
            "macro_intelligence": "unavailable_in_this_build",
            "portfolio_intelligence": "this_package",
        },
    }


def evaluate_scenario(question: str, package: PortfolioPackage | None = None) -> dict[str, Any]:
    """Scenario analysis — withhold invented outcomes; document assumptions only."""
    q = (question or "").strip()
    assumptions = [
        "Holding weights from current Portfolio schema only.",
        "No fabricated return or risk deltas.",
        "Macro / Forecast engines must supply causal map — unavailable → withhold.",
    ]
    sectors: dict[str, float] = {}
    if package and package.portfolio:
        sectors = dict(package.sector_exposure) or sector_exposure(package.portfolio)
    notes: list[str] = []
    ql = q.lower()

    def _sector_note(keys: tuple[str, ...], label: str) -> None:
        matched = [(k, v) for k, v in sectors.items() if any(x in k.lower() for x in keys)]
        if matched:
            w = sum(v for _, v in matched)
            notes.append(
                f"{label} weight currently ~{w * 100:.0f}% of portfolio (from holdings sector tags). "
                "Directional impact requires Macro/Forecast engines — outcome withheld."
            )
        else:
            notes.append(f"No {label} sector weight tagged on holdings.")

    if "bank" in ql:
        _sector_note(("bank", "financial"), "Banking/Financials")
    if "oil" in ql or "energy" in ql:
        _sector_note(("energy", "oil", "gas"), "Energy")
    if "it" in ql or "technology" in ql or " techn" in ql:
        _sector_note(("it", "tech"), "IT/Technology")
    if "inflat" in ql or "rbi" in ql or "rate" in ql:
        notes.append(
            "Policy/inflation transmission not modeled without Macro Intelligence — outcome withheld."
        )

    return {
        "question": q,
        "assumptions": assumptions,
        "status": "withheld",
        "impact_notes": notes
        or [
            "Scenario outcome withheld — Forecast Layer and Macro Intelligence not available to invent impacts."
        ],
        "confidence": None,
        "evidence_refs": [],
        "disclaimer": "Never invent scenarios. Reuse Forecast/Macro/Portfolio Intelligence when present.",
    }


def build_portfolio_package(
    *,req: PortfolioIngestRequest | None = None,
    snapshot: PortfolioSnapshot | None = None,
    prior_holding_research: list[dict[str, Any]] | None = None,
) -> PortfolioPackage:
    """Build PortfolioPackage from ingest request or existing snapshot."""
    if snapshot is None:
        if req is None:
            raise ValueError("req or snapshot required")
        snapshot = ingest_to_snapshot(req)

    sectors = sector_exposure(snapshot)
    holding_research = _seed_holding_research(snapshot, prior_holding_research)
    research_score = _research_score(holding_research)
    div_score = _pct(_diversification_01(sectors))
    covered = sum(1 for r in holding_research if not r.get("missing"))
    coverage_pct = int(round(100 * covered / max(1, len(snapshot.holdings)))) if snapshot.holdings else 0
    health = _health_score(research_score, div_score, coverage_pct)

    withheld = [
        "Forecast Score (Forecast Layer unavailable)",
        "Risk Score (risk engine inputs unavailable)",
        "Fabricated returns / performance",
        "Buy/Sell/Execute language",
        "Invented scenario outcomes",
    ]
    if covered == 0:
        withheld.append("Holding-level equity research (deferred — not fabricated)")

    draft = PortfolioPackage(
        portfolio=snapshot,
        health_score=health,
        research_score=research_score,
        forecast_score=None,
        risk_score=None,
        diversification_score=div_score,
        sector_exposure=sectors,
        macro_exposure={
            "status": "withheld",
            "note": "Macro factor map not wired — exposure not fabricated.",
        },
        holding_research=holding_research,
        monitoring={
            "policy": "Surface meaningful changes only.",
            "status": "scaffold",
            "detectors": [
                "forecast_changes",
                "risk_changes",
                "valuation_changes",
                "business_deterioration",
                "business_improvement",
                "earnings",
                "corporate_actions",
                "macro_impacts",
                "sector_changes",
                "governance_events",
                "management_commentary",
            ],
            "note": "Continuous monitoring requires stored baselines + market feeds. Not fabricated.",
        },
        scenarios=[_scenario_scaffold()],
        workspace={"mode": "portfolio_office", "tabs": WORKSPACE_TABS},
        components_reused=list(COMPONENTS_REUSED),
        withheld=withheld,
        notes=list(snapshot.notes)
        + [
            "Portfolio Office does not execute trades.",
            f"Model catalog available: {', '.join(MODEL_PORTFOLIOS.keys())}.",
            "Broker integration is architectural only (source=broker_future).",
        ],
        evidence=[
            f"holdings_count={len(snapshot.holdings)}",
            f"source={snapshot.source}",
            f"sectors={len(sectors)}",
        ],
        confidence=health if health is not None else 40,
    )

    attach_to_package(draft)
    draft.health_summary = _executive_health(
        snapshot, sectors, holding_research, draft.recommendations
    )
    draft.monthly_report = _monthly_report(snapshot, draft.recommendations, holding_research)
    draft.timeline = _timeline_seed(snapshot, health, research_score)
    draft.client_dashboard = {
        "portfolio_health": health,
        "todays_changes": {"status": "withheld", "note": "Needs prior-day baseline."},
        "research_feed": [r for r in holding_research if not r.get("missing")],
        "risk_feed": {"status": "withheld"},
        "forecast_feed": {"status": "withheld"},
        "upcoming_events": {"status": "withheld"},
        "action_center": draft.action_center,
        "monthly_report_available": True,
        "timeline_available": True,
    }
    draft.advisor_dashboard = {
        "clients_requiring_review": [snapshot.client_id or snapshot.name]
        if any(r.priority == "high" for r in draft.recommendations)
        else [],
        "high_priority_alerts": [r.model_dump() for r in draft.recommendations if r.priority == "high"],
        "forecast_changes": {"status": "withheld"},
        "risk_changes": {"status": "withheld"},
        "upcoming_earnings": {"status": "withheld"},
        "recent_reports": [{"type": "monthly", "as_of": snapshot.as_of.isoformat() if snapshot.as_of else None}],
        "portfolio_health_ranking": [
            {
                "name": snapshot.name,
                "client": snapshot.client_id,
                "health": health,
            }
        ],
    }
    return draft


def package_from_metadata(metadata: dict[str, Any] | None) -> PortfolioPackage | None:
    """Build package from ResearchRunCreate.metadata portfolio ingest block."""
    meta = metadata or {}
    ingest = meta.get("portfolio") or meta.get("portfolio_ingest")
    if not ingest and not meta.get("holdings") and not meta.get("csv_text") and not meta.get("model_id"):
        return None
    if isinstance(ingest, dict):
        req = PortfolioIngestRequest(**ingest)
    else:
        req = PortfolioIngestRequest(
            name=meta.get("name") or "Client Portfolio",
            client_id=meta.get("client_id"),
            source=meta.get("source") or ("model" if meta.get("model_id") else "manual"),
            holdings=meta.get("holdings") or [],
            csv_text=meta.get("csv_text"),
            model_id=meta.get("model_id"),
        )
    prior = meta.get("holding_research") or meta.get("prior_holding_research")
    return build_portfolio_package(req=req, prior_holding_research=prior)


def attach_portfolio_to_run(run: ResearchRun, package: PortfolioPackage) -> ResearchRun:
    run.portfolio = package
    run.metadata = {
        **(run.metadata or {}),
        "portfolio_office": True,
        "portfolio_id": package.portfolio.portfolio_id if package.portfolio else None,
        "health_score": package.health_score,
        "recommendation_count": len(package.recommendations),
    }
    return run
