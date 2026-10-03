"""Phase 3.4 Research Intelligence orchestrator — executive research note order."""

from __future__ import annotations

import re
from typing import Any, Optional

from investment_intelligence.policy import assert_no_recommendation, strip_recommendation_language

from research_intelligence import engines
from research_intelligence.corpus import get_corpus, list_entities, resolve_entity
from research_intelligence.schema import (
    ASK_WIRED,
    RI_VERSION,
    RECOMMENDATION_POLICY,
    ResearchPackage,
)


_FORECAST_RE = re.compile(
    r"("
    r"\bwhat will\b|"
    r"\bwill .+ (beat|outperform|grow|report|earn)\b|"
    r"\bwill margins?\b|"
    r"\bnext quarter\b|"
    r"\bbeat expectations\b|"
    r"\bpredict\b.+\b(earnings|revenue|margin|volume|growth|print)\b|"
    r"\bpredict\b.+\bnext\b|"
    r"\bforecast\b.+\b(earnings|revenue|margin|eps|nim|growth|volume)\b|"
    r"\bforecast\b.+\bnext\b|"
    r"\bwill .+ margins? (increase|improve|rise|expand)\b"
    r")",
    re.I,
)
_RECO_ASK_RE = re.compile(
    r"("
    r"\bbuy or sell\b|"
    r"\bshould i (buy|sell)\b|"
    r"\btarget price\b|"
    r"\bprice target\b|"
    r"\bis .+ a (buy|sell)\b|"
    r"\bprovide a buy\b|"
    r"\bgive me a (buy|sell|price target)\b|"
    r"\brating\b|"
    r"\boverweight\b|"
    r"\bunderweight\b|"
    r"\bbuy recommendation\b|"
    r"\b(buy|sell) rating\b"
    r")",
    re.I,
)


def detect_intents(question: str) -> list[str]:
    q = (question or "").lower()
    intents: list[str] = []
    # Policy refusals first — never answer forecasts or BUY/SELL as research.
    # Skip when the question is *about* the no-forecast / no-reco policy itself.
    meta_policy = bool(
        re.search(
            r"\b(without forecasting|does not forecast|no forecasting|not forecast|"
            r"recommendation policy|observations only|no buy/?sell)\b",
            q,
        )
    )
    if _RECO_ASK_RE.search(q) and not meta_policy:
        intents.append("refuse_recommendation")
    if _FORECAST_RE.search(q) and not meta_policy:
        intents.append("refuse_forecast")
    # Knowledge evolution before generic "evolution" deep-research matches
    if re.search(r"\b(knowledge evolution|updates knowledge|learning becomes|long-lived|from research to)\b", q):
        intents.append("knowledge_evolution")
    if re.search(
        r"\b(deep research|five years|5 years|10 years|fy2022|fy2026|fy23|fy24|"
        r"management evolution|industry evolution|competitive evolution|risk evolution|"
        r"consistently emphasized|recurring themes?|guidance vs delivery|"
        r"business evolution|strategy evolution)\b",
        q,
    ):
        intents.append("deep_research")
    if re.search(
        r"\b(annual report|fy20|business model|business segments?|strategic priorit|"
        r"segments?|governance|financial changes|from the annual report)\b",
        q,
    ):
        intents.append("annual_report")
    if re.search(
        r"\b(transcript|earnings call|conference call|management commentary|"
        r"analyst (questions?|q&a)|pricing commentary|demand commentary|"
        r"hiring commentary|margin commentary|competition commentary)\b",
        q,
    ):
        intents.append("transcript")
    if re.search(
        r"\b(management|ceo|cfo|chairman|leadership|communication|execution|"
        r"philosophy|management consistency|capital allocation discipline)\b",
        q,
    ):
        intents.append("management")
    if re.search(
        r"\b(guidance|vs consensus|vs actual|vs previous|revenue guidance|"
        r"margin guidance|capex guidance|hiring guidance|pricing guidance|"
        r"demand commentary|guidance changed|guidance evolved)\b",
        q,
    ):
        intents.append("guidance")
    if re.search(
        r"\b(estimate|consensus|revision|expectation gap|ebitda|eps|"
        r"estimate changes|margin revisions)\b",
        q,
    ):
        intents.append("estimates")
    if re.search(
        r"\b(event|acquisition|divestiture|buyback|dividend|capital raise|"
        r"debt issue|litigation|product launch|regulatory action|factory|"
        r"management change)\b",
        q,
    ):
        intents.append("events")
    if re.search(
        r"\b(research memory|remember|company history|never duplicate|conclusions|"
        r"what changed since|how has management evolved|how has capital allocation changed|"
        r"how has guidance changed|last quarter)\b",
        q,
    ):
        intents.append("memory")
    if re.search(
        r"\b(cross-?document|document linkage|investor (presentation|day)|"
        r"press release|filings?|one timeline|compare .+ annual|"
        r"q1 fy|q2 fy|q3 fy|q4 fy)\b",
        q,
    ):
        intents.append("cross_document")
    if re.search(
        r"\b(timeline|chronolog|ipo|major (events|risks)|important decisions|"
        r"history of|leadership history)\b",
        q,
    ):
        intents.append("timeline")
    if re.search(r"\b(research quality|freshness|coverage|contradiction|completeness|missing information)\b", q):
        intents.append("quality")
    if re.search(r"\b(capital allocat\w*)\b", q):
        intents.append("deep_research")
        intents.append("annual_report")
    if re.search(r"\b(research object|workspace|canonical research)\b", q):
        intents.append("research_object")
    if re.search(r"\b(monitor|monitoring)\b", q):
        intents.append("monitoring")
    if not intents:
        intents.append("overview")
    seen: set[str] = set()
    out: list[str] = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _refusal_package(question: str, *, kind: str, entity: Optional[str], company: Optional[str]) -> dict[str, Any]:
    if kind == "refuse_recommendation":
        summary = strip_recommendation_language(
            "Research Intelligence does not issue BUY/SELL recommendations, ratings, or target prices. "
            "Recommendation policy is observations_only_no_buy_sell. "
            "Ask instead about structured research memory — annual reports, transcripts, guidance history, "
            "events, timelines, or deep research synthesis. Unknown: any future price path."
        )
        unknowns = [
            "Future prices and ratings are outside Research Intelligence scope",
            "No BUY/SELL recommendation will be issued",
        ]
    else:
        summary = strip_recommendation_language(
            "Research Intelligence refuses forward-looking earnings/margin forecasts. "
            "It structures historical guidance, estimate revisions, and expectation gaps — "
            "it does not predict what a company will report next quarter or whether it will beat expectations. "
            "Unknown: next-period outcomes. Observations only — no BUY/SELL."
        )
        unknowns = [
            "Next-quarter / forward outcomes are unknown",
            "No forecast is issued — historical comparison only",
        ]
    pkg = ResearchPackage(
        ok=True,
        question=question,
        entity=entity,
        company=company,
        modules_used=[kind, "policy"],
        executive_summary=summary,
        whats_new=["Policy refusal — no forecast/recommendation content generated"],
        business_impact="Not applicable — refused under research/recommendation policy.",
        financial_impact="Not applicable — no forward financial prediction issued.",
        industry_impact="Not applicable.",
        investment_implications=(
            "Investment implications are observational only when research memory is requested; "
            "this question was refused under policy."
        ),
        evidence={
            "sources": [{"source": "recommendation_policy", "type": "policy"}],
            "strength": "policy",
            "summary": "Refusal grounded in recommendation / no-forecast policy.",
        },
        unknowns=unknowns,
        monitoring_points=["Re-ask as historical guidance, estimate revision, or research memory question"],
        recommendation=None,
        recommendation_policy=RECOMMENDATION_POLICY,
        ask_wired=ASK_WIRED,
        confidence=0.99,
        fabricated=False,
        summary=summary,
    )
    out = pkg.to_dict()
    out["version"] = RI_VERSION
    out["policy_refuse"] = True
    out["refuse_kind"] = kind
    out["executive_note_order"] = [
        "executive_summary",
        "whats_new",
        "business_impact",
        "financial_impact",
        "industry_impact",
        "investment_implications",
        "evidence",
        "unknowns",
        "monitoring_points",
    ]
    assert_no_recommendation(out)
    return out


def analyse(question: str, *, entity: Optional[str] = None) -> dict[str, Any]:
    intents = detect_intents(question)
    key = entity or resolve_entity(question)
    pkg = ResearchPackage(ok=False, question=question, recommendation_policy=RECOMMENDATION_POLICY)

    # Policy refusals — even when entity resolves.
    if "refuse_recommendation" in intents:
        c = get_corpus(key) if key else None
        return _refusal_package(
            question,
            kind="refuse_recommendation",
            entity=key,
            company=(c or {}).get("name"),
        )
    if "refuse_forecast" in intents:
        c = get_corpus(key) if key else None
        return _refusal_package(
            question,
            kind="refuse_forecast",
            entity=key,
            company=(c or {}).get("name"),
        )

    if not key:
        pkg.executive_summary = (
            "Research Intelligence needs a supported company "
            "(Reliance, TCS, Infosys, HDFC Bank, Asian Paints). "
            "Ask about annual reports, transcripts, guidance, management, events, "
            "timeline, deep research, or research memory. No BUY/SELL recommendations are issued."
        )
        pkg.summary = pkg.executive_summary
        pkg.unknowns = ["Entity not resolved"]
        pkg.confidence = 0.25
        return pkg.to_dict()

    c = get_corpus(key)
    assert c is not None
    pkg.entity = key
    pkg.company = c["name"]
    modules: list[str] = []

    # Always attach workspace object + quality + memory scaffolding
    robj = engines.research_object(c)
    pkg.research_object = robj["research_object"]
    modules.append("research_object")

    ar = engines.annual_report_intelligence(c)
    pkg.annual_report = ar
    modules.append("annual_report")

    tx = engines.transcript_intelligence(c)
    pkg.transcript = tx
    modules.append("transcript")

    mg = engines.management_intelligence(c)
    pkg.management = mg
    modules.append("management")

    gd = engines.guidance_intelligence(c)
    pkg.guidance = gd
    modules.append("guidance")

    est = engines.estimate_intelligence(c)
    pkg.estimates = est
    modules.append("estimates")

    ev = engines.event_intelligence(c)
    pkg.events = ev
    modules.append("events")

    mem = engines.research_memory(c)
    pkg.memory = mem
    modules.append("memory")

    xd = engines.cross_document(c)
    pkg.cross_document = xd
    modules.append("cross_document")

    tl = engines.timeline_engine(c)
    pkg.timeline = tl
    modules.append("timeline")

    ql = engines.quality_engine(c)
    pkg.quality = ql
    modules.append("quality")

    ke = engines.knowledge_evolution(c)
    pkg.knowledge_evolution = ke
    modules.append("knowledge_evolution")

    dr = engines.deep_research(c)
    pkg.deep_research = dr
    modules.append("deep_research")

    brief = engines.executive_brief_bits(c)
    pkg.whats_new = list(brief["whats_new"])
    pkg.business_impact = brief["business_impact"]
    pkg.financial_impact = brief["financial_impact"]
    pkg.industry_impact = brief["industry_impact"]
    pkg.investment_implications = brief["investment_implications"]
    pkg.unknowns = list(c.get("unknowns") or [])[:8]
    pkg.monitoring_points = list(c.get("monitoring") or [])[:8]
    pkg.evidence = {
        "sources": c.get("documents") or [],
        "strength": (ql.get("dimensions") or {}).get("research_completeness"),
        "summary": f"Evidence for {c['name']} is structured from Research Memory corpus documents and extracts.",
    }

    intent_map = {
        "deep_research": dr["summary"],
        "annual_report": ar["summary"],
        "transcript": tx["summary"],
        "management": mg["summary"],
        "guidance": gd["summary"],
        "estimates": est["summary"],
        "events": ev["summary"],
        "memory": mem["summary"],
        "cross_document": xd["summary"],
        "timeline": tl["summary"],
        "quality": ql["summary"],
        "knowledge_evolution": ke["summary"],
        "research_object": robj["summary"],
        "monitoring": strip_recommendation_language(
            f"Monitoring points for {c['name']}: " + "; ".join(pkg.monitoring_points)
            + ". Track business/financial/industry changes via Research Memory updates. Observations only."
        ),
        "overview": strip_recommendation_language(
            f"Executive research note for {c['name']}: {'; '.join((c.get('memory') or {}).get('conclusions') or [])}. "
            f"What's new — {'; '.join(pkg.whats_new[:2])}. "
            f"Recurring themes — {', '.join(((c.get('memory') or {}).get('recurring_themes') or [])[:5])}. "
            f"Research is structured institutional memory, not document summarization. No BUY/SELL."
        ),
    }
    primary = intents[0]
    summary = intent_map.get(primary) or intent_map["overview"]

    # Surface quarter/period deltas when the question asks what changed.
    qlow = (question or "").lower()
    if re.search(r"\b(what changed|since last quarter|how has .+ changed)\b", qlow):
        delta_bits = []
        if pkg.whats_new:
            delta_bits.append("What changed — " + "; ".join(pkg.whats_new[:3]))
        if gd.get("evolution"):
            delta_bits.append(f"Guidance change — {gd.get('evolution')}")
        mem_body = (mem.get("memory") if isinstance(mem, dict) else None) or (c.get("memory") or {})
        if mem_body.get("guidance_history_note"):
            delta_bits.append(f"Guidance history — {mem_body.get('guidance_history_note')}")
        if "quarter" not in summary.lower():
            delta_bits.append("Quarter/FY research memory is updated in place — never duplicated.")
        if delta_bits:
            summary = strip_recommendation_language(
                " ".join(delta_bits) + " " + summary
            )

    pkg.executive_summary = strip_recommendation_language(summary)[:1400]
    pkg.summary = pkg.executive_summary
    pkg.modules_used = []
    seen: set[str] = set()
    for m in modules:
        if m not in seen:
            seen.add(m)
            pkg.modules_used.append(m)
    if "monitoring" in intents and "monitoring" not in pkg.modules_used:
        pkg.modules_used.append("monitoring")
    pkg.ok = bool(pkg.executive_summary)
    pkg.confidence = float((ql.get("dimensions") or {}).get("confidence") or 0.85)
    pkg.fabricated = False
    pkg.recommendation = None
    pkg.recommendation_policy = RECOMMENDATION_POLICY
    pkg.ask_wired = ASK_WIRED

    out = pkg.to_dict()
    out["executive_summary"] = strip_recommendation_language(out.get("executive_summary") or "")
    out["summary"] = out["executive_summary"]
    out["recommendation"] = None
    out["recommendation_policy"] = RECOMMENDATION_POLICY
    out["ask_wired"] = ASK_WIRED
    out["version"] = RI_VERSION
    out["available_entities"] = list_entities()
    out["executive_note_order"] = [
        "executive_summary",
        "whats_new",
        "business_impact",
        "financial_impact",
        "industry_impact",
        "investment_implications",
        "evidence",
        "unknowns",
        "monitoring_points",
    ]
    if not assert_no_recommendation(out):
        out["executive_summary"] = strip_recommendation_language(
            (out.get("executive_summary") or "")
            + " Observations only under recommendation policy (no buy / no sell)."
        )
        out["summary"] = out["executive_summary"]
    return out
