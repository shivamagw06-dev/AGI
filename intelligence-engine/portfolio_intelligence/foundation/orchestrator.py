"""Phase 3.3 Portfolio Intelligence orchestrator — executive brief order.

Consumes Investment Intelligence profiles via quality engine.
Ask/KUL integration deferred until Acceptance = 100%.
Never issues BUY/SELL or trade recommendations.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from investment_intelligence.policy import assert_no_recommendation, strip_recommendation_language

from portfolio_intelligence.foundation import engines
from portfolio_intelligence.foundation.catalog import get_portfolio, resolve_portfolio
from portfolio_intelligence.foundation.schema import (
    ASK_WIRED,
    PI_VERSION,
    PortfolioPackage,
    RECOMMENDATION_POLICY,
)


def detect_intents(question: str) -> list[str]:
    q = (question or "").lower()
    intents: list[str] = []
    if re.search(r"\b(compare|versus|vs\.?|two portfolios?)\b", q):
        intents.append("compare")
    if re.search(r"\b(dominat\w*|largest risk|risk contribution|which holdings)\b", q):
        intents.append("dominating_risk")
    if re.search(r"\b(rebalanc\w*|drift|what changed)\b", q):
        intents.append("rebalancing")
    if re.search(r"\b(attribut\w*|outperform|underperform|performance)\b", q):
        intents.append("attribution")
    if re.search(
        r"\b(scenarios?|shock|recession|recovery|bull|bear|interest.?rate|commodity|fx|regulatory|technology disruption)\b",
        q,
    ):
        intents.append("scenarios")
    if re.search(r"\b(monitor|watching|deteriorat\w*|evidence freshness)\b", q):
        intents.append("monitoring")
    if re.search(r"\b(correlat\w*|hidden concentration|diversification benefit)\b", q):
        intents.append("correlation")
    if re.search(
        r"\b(risk budget|tail risk|drawdown|liquidity risk|position risk|sector risk|factor risk|concentration risk)\b",
        q,
    ):
        intents.append("risk")
    if re.search(
        r"\b(exposure|style|factor|currency|interest rate|commodity|market cap|geography|country)\b",
        q,
    ):
        intents.append("exposure")
    if re.search(
        r"\b(portfolio quality|business quality|financial quality|evidence strength|cash generation)\b",
        q,
    ):
        intents.append("quality")
    if re.search(
        r"\b(construct\w*|sizing|conviction|allocation logic|why hold|diversif\w*|concentrat\w*|sector balance|cash)\b",
        q,
    ):
        intents.append("construction")
    if re.search(r"\b(graph|relationship|knowledge graph)\b", q):
        intents.append("graph")
    if re.search(r"\b(portfolio object|canonical portfolio|holdings)\b", q):
        intents.append("portfolio_object")
    if not intents:
        intents.append("overview")
    seen: set[str] = set()
    out: list[str] = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def analyse(
    question: str,
    *,
    portfolio_id: Optional[str] = None,
    compare_with: Optional[str] = None,
) -> dict[str, Any]:
    intents = detect_intents(question)
    pid = portfolio_id or resolve_portfolio(question)
    p = get_portfolio(pid)
    pkg = PortfolioPackage(ok=False, question=question, recommendation_policy=RECOMMENDATION_POLICY)

    if not p:
        pkg.portfolio_summary = (
            "Portfolio Intelligence needs a supported portfolio "
            "(e.g. AGIB Core India Equity or AGIB Concentrated Growth). "
            "Ask about diversification, exposures, risk, correlation, quality, "
            "attribution, scenarios, or monitoring. No BUY/SELL recommendations are issued."
        )
        pkg.summary = pkg.portfolio_summary
        pkg.unknowns = ["Portfolio not resolved"]
        pkg.confidence = 0.25
        return pkg.to_dict()

    pkg.portfolio_id = p["portfolio_id"]
    pkg.portfolio_name = p["name"]
    modules: list[str] = []

    # Always build canonical object + core layers for executive brief
    obj = engines.portfolio_object(p)
    pkg.portfolio_object = obj["portfolio_object"]
    modules.append("portfolio_object")

    cons = engines.construction(p)
    pkg.construction = cons
    pkg.diversification = cons.get("diversification")
    modules.append("construction")

    exp = engines.exposures(p)
    pkg.exposures = exp
    pkg.sector_exposures = exp.get("sector_exposure")
    modules.append("exposures")

    risk = engines.risk_budget(p)
    pkg.risk_budget = risk
    pkg.key_risks = list(risk.get("key_risks") or [])[:8]
    modules.append("risk_budget")

    corr = engines.correlation(p)
    pkg.correlation = corr
    modules.append("correlation")

    ql = engines.quality(p)
    pkg.quality = ql
    modules.append("quality")

    attrib = engines.attribution(p)
    pkg.attribution = attrib
    modules.append("attribution")

    rebal = engines.rebalancing(p)
    pkg.rebalancing = rebal
    modules.append("rebalancing")

    sc = engines.scenarios(p)
    pkg.scenarios = sc
    modules.append("scenarios")

    mon = engines.monitoring(p)
    pkg.monitoring = mon
    pkg.monitoring_priorities = list(mon.get("priorities") or [])[:8]
    modules.append("monitoring")

    g = engines.graph(p)
    pkg.graph = g
    modules.append("graph")

    summary = ""
    primary = intents[0]

    if "compare" in intents:
        other_id = compare_with or (
            "agib_concentrated_growth" if p["portfolio_id"] == "agib_core_india" else "agib_core_india"
        )
        other = get_portfolio(other_id)
        if other:
            cmp = engines.compare_portfolios(p, other)
            pkg.compare = cmp
            modules.append("compare")
            summary = cmp["summary"]

    if "dominating_risk" in intents:
        dom = engines.dominating_risk_holdings(p)
        pkg.compare = {**(pkg.compare or {}), "dominating_risk": dom}
        modules.append("dominating_risk")
        if not summary or primary == "dominating_risk":
            summary = dom["summary"]

    intent_summary_map = {
        "rebalancing": rebal["summary"],
        "attribution": attrib["summary"],
        "scenarios": sc["summary"],
        "monitoring": mon["summary"],
        "correlation": corr["summary"],
        "risk": risk["summary"],
        "exposure": exp["summary"],
        "quality": ql["summary"],
        "construction": cons["summary"],
        "graph": g["summary"],
        "portfolio_object": obj["summary"],
        "overview": (
            f"Portfolio Summary for {p['name']}: {len(p['holdings'])} holdings, "
            f"cash {float(p.get('cash_weight') or 0):.0%}, benchmark {p.get('benchmark')}. "
            f"Diversification: top-3 concentration "
            f"{(cons.get('diversification') or {}).get('top3_concentration', 0):.0%}; "
            f"sectors span { (cons.get('diversification') or {}).get('sector_count', 0)} sleeves. "
            f"Key risks: {', '.join(pkg.key_risks[:3])}. "
            f"Sector exposures: "
            + ", ".join(
                f"{k} {v:.0%}"
                for k, v in sorted((pkg.sector_exposures or {}).items(), key=lambda kv: -kv[1])[:4]
                if k != "cash"
            )
            + ". Monitoring priorities include business/industry deterioration and macro exposure. "
            + "Evidence is fixture-backed and observational. Unknowns include live NAV marks. "
            + "No BUY/SELL — observations only."
        ),
    }
    if not summary:
        summary = intent_summary_map.get(primary) or intent_summary_map["overview"]
    elif primary in intent_summary_map and primary not in ("compare", "dominating_risk"):
        # Prefer primary intent summary when not already set by compare/risk-dominate
        if primary != "overview":
            summary = intent_summary_map[primary]

    pkg.portfolio_summary = strip_recommendation_language(summary)[:1100]
    pkg.summary = pkg.portfolio_summary
    pkg.evidence = {
        "sources": [
            {"source": "portfolio_object", "type": "canonical", "portfolio_id": p["portfolio_id"]},
            {"source": "investment_intelligence", "type": "quality_overlay"},
            {"source": "industry_intelligence", "type": "sector_context"},
        ],
        "strength": "structured_fixture",
        "summary": (
            f"Evidence for {p['name']} is structured from the canonical portfolio object "
            f"with Investment Intelligence quality overlays where inv_key is present."
        ),
    }
    pkg.unknowns = list(p.get("unknowns") or [])[:8]
    pkg.modules_used = []
    seen_m: set[str] = set()
    for m in modules:
        if m not in seen_m:
            seen_m.add(m)
            pkg.modules_used.append(m)
    pkg.ok = bool(pkg.portfolio_summary)
    pkg.confidence = 0.9 if pkg.ok else 0.2
    pkg.fabricated = False
    pkg.recommendation = None
    pkg.recommendation_policy = RECOMMENDATION_POLICY
    pkg.ask_wired = ASK_WIRED

    out = pkg.to_dict()
    out["portfolio_summary"] = strip_recommendation_language(out.get("portfolio_summary") or "")
    out["summary"] = out["portfolio_summary"]
    out["recommendation"] = None
    out["recommendation_policy"] = RECOMMENDATION_POLICY
    out["ask_wired"] = ASK_WIRED
    out["version"] = PI_VERSION
    out["executive_brief_order"] = [
        "portfolio_summary",
        "diversification",
        "key_risks",
        "sector_exposures",
        "monitoring_priorities",
        "evidence",
        "unknowns",
    ]
    if not assert_no_recommendation(out):
        out["portfolio_summary"] = strip_recommendation_language(
            (out.get("portfolio_summary") or "")
            + " Observations only under recommendation policy (no buy / no sell)."
        )
        out["summary"] = out["portfolio_summary"]
    return out
