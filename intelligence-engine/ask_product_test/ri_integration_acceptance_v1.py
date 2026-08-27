"""Research Integration Acceptance Suite v1.0 - 100 live questions via KUL.

Phase 3.4.5 gate: Research Intelligence registered as first-class KUL provider,
research questions routed to RI before generic retrieval, no BUY/SELL leakage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from investment_intelligence.policy import has_recommendation_leak

RI_INTEGRATION_CASES: List[Dict[str, Any]] = []


def _add(category: str, prompt: str, *, must_any: List[str], require_ri: bool = True):
    RI_INTEGRATION_CASES.append(
        {
            "id": f"RII-{len(RI_INTEGRATION_CASES)+1:02d}",
            "category": category,
            "prompt": prompt,
            "require_ri": require_ri,
            "must_any": must_any,
        }
    )


# Annual Reports (12)
for prompt, must in [
    (
        "From the annual report, summarize Reliance's business segments and strategic priorities.",
        ["annual", "reliance", "segments", "strategic"],
    ),
    (
        "Use TCS annual report research to explain its business model and financial changes.",
        ["annual", "tcs", "business", "financial"],
    ),
    (
        "What does the Infosys annual report say about strategic priorities and risks?",
        ["annual", "infosys", "strategic", "risk"],
    ),
    (
        "From HDFC Bank's annual report, summarize asset quality, capital, and governance signals.",
        ["annual", "hdfc", "asset", "capital"],
    ),
    (
        "Use Asian Paints annual report intelligence to explain distribution and raw material themes.",
        ["annual", "asian", "distribution", "material"],
    ),
    (
        "How has Reliance capital allocation evolved across annual report research memory?",
        ["annual", "reliance", "capital", "allocation"],
    ),
    (
        "From TCS annual reports, what recurring themes show up in cash generation and margins?",
        ["annual", "tcs", "cash", "margin"],
    ),
    (
        "Use Infosys annual report evidence to summarize risk disclosures and operating priorities.",
        ["annual", "infosys", "risk", "operating"],
    ),
    (
        "What does HDFC Bank annual report research show about deposits and credit discipline?",
        ["annual", "hdfc", "deposit", "credit"],
    ),
    (
        "From Asian Paints annual reports, explain business segments and pricing resilience.",
        ["annual", "asian", "segments", "pricing"],
    ),
    (
        "Use Reliance annual report research to summarize governance, capex, and debt signals.",
        ["annual", "reliance", "governance", "capex"],
    ),
    (
        "What does TCS annual report research memory say about workforce, utilization, and margins?",
        ["annual", "tcs", "workforce", "margin"],
    ),
]:
    _add("annual_reports", prompt, must_any=must)


# Transcripts (12)
for prompt, must in [
    (
        "Using the latest Reliance earnings transcript, summarize management commentary on retail and energy.",
        ["transcript", "reliance", "management", "retail"],
    ),
    (
        "From the TCS earnings call transcript, what did management say about demand and margins?",
        ["transcript", "tcs", "demand", "margin"],
    ),
    (
        "Use Infosys conference call transcript research to summarize guidance and hiring commentary.",
        ["transcript", "infosys", "guidance", "hiring"],
    ),
    (
        "From HDFC Bank earnings transcript, explain deposit and NIM management commentary.",
        ["transcript", "hdfc", "deposit", "nim"],
    ),
    (
        "Use Asian Paints transcript intelligence to summarize pricing and volume commentary.",
        ["transcript", "asian", "pricing", "volume"],
    ),
    (
        "What changed in Reliance management commentary across earnings call transcripts?",
        ["transcript", "reliance", "changed", "management"],
    ),
    (
        "From TCS transcript Q&A, summarize analyst questions on discretionary demand.",
        ["transcript", "tcs", "analyst", "demand"],
    ),
    (
        "Use Infosys earnings transcript memory to explain margin commentary and deal pipeline.",
        ["transcript", "infosys", "margin", "deal"],
    ),
    (
        "From HDFC Bank conference call transcript, summarize credit cost and deposit commentary.",
        ["transcript", "hdfc", "credit", "deposit"],
    ),
    (
        "Use Asian Paints earnings call transcript to explain competitive intensity commentary.",
        ["transcript", "asian", "competition", "commentary"],
    ),
    (
        "What did Reliance transcript research say about capex and digital services commentary?",
        ["transcript", "reliance", "capex", "digital"],
    ),
    (
        "From TCS earnings transcript research, summarize CEO commentary and guidance tone.",
        ["transcript", "tcs", "ceo", "guidance"],
    ),
]:
    _add("transcripts", prompt, must_any=must)


# Management (10)
for prompt, must in [
    (
        "Use management intelligence to assess Reliance leadership communication consistency.",
        ["management", "reliance", "leadership", "consistency"],
    ),
    (
        "From TCS management commentary, explain execution philosophy and capital discipline.",
        ["management", "tcs", "execution", "capital"],
    ),
    (
        "Use Infosys management intelligence to summarize CEO and CFO communication priorities.",
        ["management", "infosys", "ceo", "cfo"],
    ),
    (
        "What does HDFC Bank management commentary show about credit discipline and deposits?",
        ["management", "hdfc", "credit", "deposit"],
    ),
    (
        "Use Asian Paints management intelligence to assess pricing and distribution philosophy.",
        ["management", "asian", "pricing", "distribution"],
    ),
    (
        "How has Reliance management philosophy evolved in research memory?",
        ["management", "reliance", "evolved", "memory"],
    ),
    (
        "Use TCS transcript and annual report management research to assess communication quality.",
        ["management", "tcs", "transcript", "annual"],
    ),
    (
        "What does Infosys management consistency look like across guidance history?",
        ["management", "infosys", "consistency", "guidance"],
    ),
    (
        "Use HDFC Bank management intelligence to summarize capital allocation discipline.",
        ["management", "hdfc", "capital", "discipline"],
    ),
    (
        "From Asian Paints management commentary, explain execution strengths and unknowns.",
        ["management", "asian", "execution", "unknown"],
    ),
]:
    _add("management", prompt, must_any=must)


# Guidance (10)
for prompt, must in [
    (
        "Summarize Reliance guidance history and how guidance evolved versus delivery.",
        ["guidance", "reliance", "history", "delivery"],
    ),
    (
        "Use TCS guidance history to explain demand commentary versus actual delivery.",
        ["guidance", "tcs", "demand", "delivery"],
    ),
    (
        "How has Infosys margin guidance changed across research memory?",
        ["guidance", "infosys", "margin", "changed"],
    ),
    (
        "Use HDFC Bank guidance history to summarize NIM and deposit commentary.",
        ["guidance", "hdfc", "nim", "deposit"],
    ),
    (
        "From Asian Paints guidance history, explain volume and pricing commentary evolution.",
        ["guidance", "asian", "volume", "pricing"],
    ),
    (
        "Compare Reliance guidance changed since last quarter with research memory conclusions.",
        ["guidance", "reliance", "quarter", "memory"],
    ),
    (
        "Use TCS guidance intelligence to summarize hiring guidance and margin outlook commentary.",
        ["guidance", "tcs", "hiring", "margin"],
    ),
    (
        "What does Infosys guidance history show about revenue guidance versus consensus?",
        ["guidance", "infosys", "revenue", "consensus"],
    ),
    (
        "Use HDFC Bank guidance intelligence to explain credit growth and risk commentary.",
        ["guidance", "hdfc", "credit", "risk"],
    ),
    (
        "How has Asian Paints guidance evolved across transcript and annual report research?",
        ["guidance", "asian", "transcript", "annual"],
    ),
]:
    _add("guidance", prompt, must_any=must)


# Estimates (8)
for prompt, must in [
    (
        "Use Reliance estimate intelligence to summarize consensus revisions and expectation gaps.",
        ["estimate", "reliance", "consensus", "gap"],
    ),
    (
        "From TCS estimate intelligence, explain EPS and margin revision themes.",
        ["estimate", "tcs", "eps", "margin"],
    ),
    (
        "Use Infosys estimate intelligence to summarize revenue expectations versus guidance.",
        ["estimate", "infosys", "revenue", "guidance"],
    ),
    (
        "What does HDFC Bank estimate intelligence show about NIM and credit cost expectations?",
        ["estimate", "hdfc", "nim", "credit"],
    ),
    (
        "Use Asian Paints estimate intelligence to summarize volume and margin revisions.",
        ["estimate", "asian", "volume", "margin"],
    ),
    (
        "How have Reliance EBITDA estimates changed in research memory?",
        ["estimate", "reliance", "ebitda", "memory"],
    ),
    (
        "Use TCS estimate changes to explain consensus expectation gaps in demand.",
        ["estimate", "tcs", "consensus", "demand"],
    ),
    (
        "From Infosys margin revisions, summarize what estimate intelligence adds to guidance history.",
        ["estimate", "infosys", "margin", "guidance"],
    ),
]:
    _add("estimates", prompt, must_any=must)


# Events (10)
for prompt, must in [
    (
        "Use event intelligence to summarize Reliance acquisition, capex, and regulatory events.",
        ["event", "reliance", "capex", "regulatory"],
    ),
    (
        "From TCS event intelligence, explain buyback, dividend, and large deal events.",
        ["event", "tcs", "buyback", "dividend"],
    ),
    (
        "Use Infosys event intelligence to summarize management change and deal events.",
        ["event", "infosys", "management", "deal"],
    ),
    (
        "What does HDFC Bank event intelligence show about merger and regulatory milestones?",
        ["event", "hdfc", "merger", "regulatory"],
    ),
    (
        "Use Asian Paints event intelligence to summarize product launch and factory events.",
        ["event", "asian", "product", "factory"],
    ),
    (
        "Build a Reliance research event summary from annual reports and press releases.",
        ["event", "reliance", "annual", "press"],
    ),
    (
        "Use TCS event intelligence to summarize management commentary around capital return events.",
        ["event", "tcs", "management", "capital"],
    ),
    (
        "From Infosys event research, explain litigation, management, and guidance events.",
        ["event", "infosys", "litigation", "guidance"],
    ),
    (
        "Use HDFC Bank event intelligence to summarize capital raise and credit events.",
        ["event", "hdfc", "capital", "credit"],
    ),
    (
        "What Asian Paints events matter across transcript, annual report, and research memory?",
        ["event", "asian", "transcript", "memory"],
    ),
]:
    _add("events", prompt, must_any=must)


# Research Memory (10)
for prompt, must in [
    (
        "Use research memory to summarize what Reliance conclusions should not be duplicated.",
        ["memory", "reliance", "conclusions", "duplicate"],
    ),
    (
        "What does TCS research memory remember about recurring themes and unknowns?",
        ["memory", "tcs", "recurring", "unknown"],
    ),
    (
        "Use Infosys research memory to explain what changed since last quarter.",
        ["memory", "infosys", "changed", "quarter"],
    ),
    (
        "From HDFC Bank research memory, summarize company history and guidance changes.",
        ["memory", "hdfc", "history", "guidance"],
    ),
    (
        "Use Asian Paints research memory to identify recurring conclusions and monitoring points.",
        ["memory", "asian", "conclusions", "monitor"],
    ),
    (
        "How has Reliance research memory updated long-lived conclusions after new events?",
        ["memory", "reliance", "updated", "events"],
    ),
    (
        "Use TCS research memory to explain how management commentary has evolved.",
        ["memory", "tcs", "management", "evolved"],
    ),
    (
        "What should Infosys research memory carry forward from annual reports and transcripts?",
        ["memory", "infosys", "annual", "transcript"],
    ),
    (
        "Use HDFC Bank research memory to summarize monitoring points and evidence gaps.",
        ["memory", "hdfc", "monitor", "evidence"],
    ),
    (
        "How does Asian Paints research memory connect company history to current guidance?",
        ["memory", "asian", "history", "guidance"],
    ),
]:
    _add("research_memory", prompt, must_any=must)


# Cross Document (8)
for prompt, must in [
    (
        "Run cross-document research for Reliance across annual report, transcript, and investor presentation.",
        ["cross", "reliance", "annual", "transcript"],
    ),
    (
        "Use cross-document TCS intelligence to link annual reports, conference calls, and press releases.",
        ["cross", "tcs", "annual", "press"],
    ),
    (
        "For Infosys, compare annual report risk disclosures with transcript management commentary.",
        ["annual", "infosys", "transcript", "management"],
    ),
    (
        "Run cross-document HDFC Bank research linking filings, transcript, and guidance history.",
        ["cross", "hdfc", "filing", "guidance"],
    ),
    (
        "Use Asian Paints cross-document intelligence across annual report and investor day material.",
        ["cross", "asian", "annual", "investor"],
    ),
    (
        "Create one cross-document timeline for Reliance from press release, annual report, and transcript cues.",
        ["cross", "reliance", "timeline", "press"],
    ),
    (
        "Use TCS cross-document research to compare Q1 FY commentary with annual report priorities.",
        ["cross", "tcs", "q1", "annual"],
    ),
    (
        "For Infosys, link guidance history with transcript Q&A and annual report strategy.",
        ["guidance", "infosys", "transcript", "annual"],
    ),
]:
    _add("cross_document", prompt, must_any=must)


# Timeline (6)
for prompt, must in [
    (
        "Build a research timeline of major Reliance events, risks, and capital allocation decisions.",
        ["timeline", "reliance", "events", "capital"],
    ),
    (
        "Use TCS research timeline to summarize leadership history and margin events.",
        ["timeline", "tcs", "leadership", "margin"],
    ),
    (
        "Create an Infosys chronology from annual report, transcript, and management change research.",
        ["chronolog", "infosys", "annual", "management"],
    ),
    (
        "Use HDFC Bank timeline intelligence to explain merger, deposit, and credit risk milestones.",
        ["timeline", "hdfc", "merger", "credit"],
    ),
    (
        "Build an Asian Paints research timeline covering pricing, competition, and factory events.",
        ["timeline", "asian", "pricing", "competition"],
    ),
    (
        "What changed since last quarter in Reliance research timeline and guidance history?",
        ["timeline", "reliance", "quarter", "guidance"],
    ),
]:
    _add("timeline", prompt, must_any=must)


# Deep Research (8)
for prompt, must in [
    (
        "Run deep research on Reliance five years of business evolution and recurring themes.",
        ["deep", "reliance", "five", "evolution"],
    ),
    (
        "Use deep research for TCS on five years of management evolution and demand cycles.",
        ["deep", "tcs", "management", "demand"],
    ),
    (
        "Run deep research on Infosys guidance versus delivery across FY2022 to FY2026.",
        ["deep", "infosys", "guidance", "delivery"],
    ),
    (
        "Use HDFC Bank deep research to explain risk evolution and capital allocation discipline.",
        ["deep", "hdfc", "risk", "capital"],
    ),
    (
        "Run deep research on Asian Paints competitive evolution and pricing power.",
        ["deep", "asian", "competitive", "pricing"],
    ),
    (
        "Use Reliance deep research to connect annual report themes with transcript changes.",
        ["deep", "reliance", "annual", "transcript"],
    ),
    (
        "Run TCS deep research on recurring themes in margins, hiring, and large deals.",
        ["deep", "tcs", "margin", "hiring"],
    ),
    (
        "Use Asian Paints deep research to summarize guidance history and monitoring priorities.",
        ["deep", "asian", "guidance", "monitoring"],
    ),
]:
    _add("deep_research", prompt, must_any=must)


# Policy Refuse (6)
for prompt, must in [
    (
        "Using Reliance annual report research, should I BUY the stock or avoid it?",
        ["refuse", "policy", "no buy"],
    ),
    (
        "From TCS transcript research, give me a BUY rating and target price.",
        ["refuse", "policy", "no buy"],
    ),
    (
        "Using Infosys guidance history, forecast next quarter EPS and say if it is a BUY.",
        ["refuse", "policy", "no buy"],
    ),
    (
        "From HDFC Bank research memory, predict next quarter NIM and provide a buy recommendation.",
        ["refuse", "policy", "no buy"],
    ),
    (
        "Use Asian Paints deep research to forecast margins and tell me whether to BUY.",
        ["refuse", "policy", "no buy"],
    ),
    (
        "Using Reliance event intelligence, give me a price target and BUY/SELL call.",
        ["refuse", "policy", "no buy"],
    ),
]:
    _add("policy_refuse", prompt, must_any=must)


assert len(RI_INTEGRATION_CASES) == 100, len(RI_INTEGRATION_CASES)


def _summary_is_direct(summary: str) -> bool:
    s = (summary or "").strip()
    if len(s) < 24:
        return False
    low = s.lower()
    hedges = (
        "insufficient unified knowledge",
        "i don't know",
        "unable to answer",
        "no information available",
        "analyse via",
    )
    if any(h in low for h in hedges):
        return False
    if low.startswith(("framework", "intent:", "planning:")):
        return False
    return True


def _blob(payload: Dict[str, Any]) -> str:
    parts = [payload.get("summary"), " ".join(payload.get("why") or [])]
    ci = payload.get("company_intelligence") or {}
    research = ci.get("research") if isinstance(ci, dict) else {}
    if isinstance(research, dict):
        parts.append(str(research))
    for r in payload.get("provider_results") or []:
        if isinstance(r, dict) and not r.get("empty"):
            parts.append(r.get("summary") or "")
            parts.append(" ".join(r.get("why") or []))
            raw = r.get("raw") or {}
            if isinstance(raw, dict):
                for key in (
                    "entity",
                    "company",
                    "executive_summary",
                    "summary",
                    "business_impact",
                    "financial_impact",
                    "industry_impact",
                    "investment_implications",
                    "whats_new",
                    "modules_used",
                    "evidence",
                    "unknowns",
                    "monitoring_points",
                    "recommendation_policy",
                    "knowledge_authority",
                    "policy_refuse",
                    "refuse_kind",
                    "annual_report",
                    "transcript",
                    "management",
                    "guidance",
                    "estimates",
                    "events",
                    "memory",
                    "cross_document",
                    "timeline",
                    "quality",
                    "knowledge_evolution",
                    "deep_research",
                    "research_object",
                ):
                    parts.append(str(raw.get(key) or ""))
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_ri_integration_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    diag = payload.get("diagnostics") or {}
    consulted = list(diag.get("providers_consulted") or [])
    plan_ids = list(((diag.get("plan") or {}).get("provider_ids")) or [])
    text = _blob(payload)
    summary = str(payload.get("summary") or "")

    assertions: Dict[str, bool] = {}

    if case.get("require_ri"):
        assertions["ri_selected"] = "research_intelligence" in sources or (
            "research_intelligence" in consulted
        )
        assertions["kul_plan_has_ri"] = (
            "research_intelligence" in plan_ids or "research_intelligence" in consulted
        )
        assertions["ri_leads_or_used"] = (
            "research_intelligence" in sources
            or (plan_ids[:1] == ["research_intelligence"])
            or ("research_intelligence" in consulted and any(m in text for m in (case.get("must_any") or [])[:2]))
        )

    assertions["provider_ordering_ok"] = (
        "research_intelligence" not in plan_ids
        or plan_ids.index("research_intelligence")
        <= min(
            (
                plan_ids.index(p)
                for p in (
                    "investment_intelligence",
                    "business_intelligence",
                    "industry_intelligence",
                    "legacy_kip",
                )
                if p in plan_ids
            ),
            default=0,
        )
    )
    assertions["no_generic_retrieval_only"] = sources != ["legacy_kip"] and (
        "legacy_kip" not in sources or len(sources) > 1
    )
    assertions["direct_answer_first"] = _summary_is_direct(summary)
    assertions["no_hallucination"] = payload.get("fabricated") is False
    assertions["no_framework_leakage"] = not summary.lower().startswith(
        ("analyse via", "framework", "intent:", "planning:")
    )
    assertions["no_recommendation_leakage"] = not has_recommendation_leak(summary)

    must = case.get("must_any") or []
    if must:
        hits = sum(1 for m in must if m.lower() in text)
        need = 1 if len(must) <= 2 else min(2, len(must))
        assertions["topic_grounding"] = hits >= need

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "sources": sources,
        "consulted": consulted,
        "plan_ids": plan_ids,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": summary[:240],
        "pass": passed,
    }
