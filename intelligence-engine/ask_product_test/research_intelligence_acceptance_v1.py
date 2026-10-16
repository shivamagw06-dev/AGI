"""AGI Research Intelligence Acceptance Test v1.0 — 400 deterministic questions.

Permanent release gate before Research Intelligence KUL integration.
Engine-only (in-process). Target ≥95%. Hallucinations 0. Recommendation leakage 0.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from investment_intelligence.policy import has_recommendation_leak
from research_intelligence.corpus import CORPUS

RI_ACCEPTANCE_400: List[Dict[str, Any]] = []
ENTITY_KEYS = sorted(CORPUS.keys())  # asian_paints, hdfc_bank, infosys, reliance, tcs


def _add(
    section: str,
    prompt: str,
    *,
    entity: Optional[str] = None,
    must_any: List[str],
    expect_modules: Optional[List[str]] = None,
    policy_refuse: bool = False,
    fields_any: Optional[List[str]] = None,
):
    RI_ACCEPTANCE_400.append(
        {
            "id": f"RIA-{len(RI_ACCEPTANCE_400)+1:03d}",
            "section": section,
            "category": section,
            "prompt": prompt,
            "entity": entity,
            "must_any": must_any,
            "expect_modules": expect_modules or [],
            "policy_refuse": policy_refuse,
            "fields_any": fields_any or ["summary"],
        }
    )


def _n(key: str) -> str:
    return CORPUS[key]["name"]


# ---- Section A — Annual Report Intelligence (40) ----
_ar_prompts = [
    ("Explain {n}'s business segments from the annual report.", ["segment", "business", "annual"], ["annual_report"]),
    ("How does {n} describe its business model?", ["business", "strategy", "model"], ["annual_report"]),
    ("What strategic priorities did {n} discuss in annual reports?", ["strategy", "priority", "theme"], ["annual_report"]),
    ("What risks did {n} highlight in the annual report?", ["risk", "annual"], ["annual_report"]),
    ("Explain {n}'s capital allocation priorities from annual reports.", ["capital", "allocat", "annual"], ["annual_report"]),
    ("What KPIs appear in {n}'s annual report intelligence?", ["kpi", "annual"], ["annual_report"]),
    ("Explain governance notes for {n} from annual reports.", ["governance", "annual"], ["annual_report"]),
    ("What financial changes are extracted for {n} annual reports?", ["financial", "change", "annual"], ["annual_report"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _ar_prompts:
        _add("annual_reports", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section B — Earnings Transcript Intelligence (40) ----
_tx_prompts = [
    ("Structure management commentary from {n}'s latest earnings transcript.", ["management", "commentary", "transcript"], ["transcript"]),
    ("What demand commentary appears in {n} earnings calls?", ["demand", "commentary"], ["transcript"]),
    ("Track pricing commentary across {n} earnings transcripts.", ["pricing", "commentary"], ["transcript"]),
    ("Explain margin commentary in {n} transcripts.", ["margin", "commentary"], ["transcript"]),
    ("What capex commentary did {n} management provide?", ["capex", "transcript", "management"], ["transcript"]),
    ("Explain hiring commentary for {n} from earnings calls.", ["hiring", "transcript"], ["transcript"]),
    ("What analyst Q&A themes appear for {n}?", ["analyst", "question"], ["transcript"]),
    ("Convert {n} conference call content into structured intelligence.", ["transcript", "structured", "management"], ["transcript"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _tx_prompts:
        _add("transcripts", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section C — Management Intelligence (40) ----
_mg_prompts = [
    ("Explain CEO / management philosophy for {n}.", ["ceo", "philosophy", "management"], ["management"]),
    ("Assess capital allocation discipline of {n} management.", ["capital", "allocat", "management"], ["management"]),
    ("How consistent is management communication for {n}?", ["consistency", "communication", "management"], ["management"]),
    ("Evaluate execution signals for {n} management.", ["execution", "management"], ["management"]),
    ("Comment on communication quality for {n}.", ["communication", "management"], ["management"]),
    ("Track leadership changes for {n}.", ["leadership", "change", "management"], ["management"]),
    ("What has management consistently emphasized at {n}?", ["management", "emphas"], ["management"]),
    ("Explain historical accuracy of {n} management commentary.", ["historical", "accuracy", "management"], ["management"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _mg_prompts:
        _add("management", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section D — Guidance Intelligence (40) ----
_gd_prompts = [
    ("Explain revenue guidance history for {n}.", ["revenue", "guidance"], ["guidance"]),
    ("Explain margin guidance for {n}.", ["margin", "guidance"], ["guidance"]),
    ("Explain capex guidance for {n}.", ["capex", "guidance"], ["guidance"]),
    ("What demand commentary is in {n} guidance history?", ["demand", "guidance"], ["guidance"]),
    ("Explain pricing guidance / commentary for {n}.", ["pricing", "guidance"], ["guidance"]),
    ("Explain hiring guidance for {n}.", ["hiring", "guidance"], ["guidance"]),
    ("How has management guidance evolved for {n}?", ["guidance", "previous", "evol"], ["guidance"]),
    ("Compare {n} guidance versus previous, consensus, and actual framing.", ["guidance", "previous", "consensus", "actual"], ["guidance"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _gd_prompts:
        _add("guidance", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section E — Estimate Intelligence (30) ----
_est_prompts = [
    ("Explain estimate intelligence for {n} without forecasting.", ["estimate", "consensus", "forecast"], ["estimates"]),
    ("What revenue / EBITDA / EPS metrics are tracked for {n}?", ["revenue", "ebitda", "eps", "estimate"], ["estimates"]),
    ("Explain consensus changes and expectation gaps for {n}.", ["consensus", "gap", "estimate"], ["estimates"]),
    ("Describe margin revisions framing for {n} estimates.", ["margin", "revision", "estimate"], ["estimates"]),
    ("Summarize estimate revision drivers for {n}.", ["revision", "estimate", "driver"], ["estimates"]),
    ("Explain why estimate intelligence for {n} does not forecast.", ["forecast", "estimate", "comparison"], ["estimates"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _est_prompts:
        _add("estimates", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section F — Event Intelligence (40) ----
_ev_prompts = [
    ("Explain acquisition / major corporate events for {n}.", ["acquisition", "event"], ["events"]),
    ("What buyback or dividend events are structured for {n}?", ["event", "buyback", "dividend", "capital", "structured"], ["events"]),
    ("Describe capital raise or debt-related events for {n}.", ["capital", "event"], ["events"]),
    ("Map factory expansion or product-launch events for {n}.", ["event", "factory", "product", "expansion", "launch"], ["events"]),
    ("Explain management-change events for {n}.", ["management", "change", "event"], ["events"]),
    ("How do {n} events link to business, industry, investment, and portfolio?", ["event", "business", "industry", "investment", "portfolio"], ["events"]),
    ("Build event intelligence for {n}.", ["event", "link"], ["events"]),
    ("Explain the history of acquisitions for {n}.", ["acquisition", "history", "event"], ["events"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _ev_prompts:
        _add("events", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section G — Research Memory (40) ----
_mem_prompts = [
    ("What does research memory store for {n}?", ["memory", "conclusion", "theme"], ["memory"]),
    ("What changed since last quarter in {n} research memory?", ["memory", "change", "quarter", "guidance", "transcript"], ["memory"]),
    ("How has management evolved for {n} according to research memory?", ["management", "evol", "memory"], ["memory", "deep_research"]),
    ("How has capital allocation changed for {n}?", ["capital", "allocat", "change", "memory"], ["memory", "deep_research"]),
    ("How has guidance changed for {n}?", ["guidance", "change", "memory"], ["memory", "guidance"]),
    ("Explain why {n} research should never be duplicated.", ["duplicate", "memory", "update"], ["memory"]),
    ("List research conclusions and recurring themes for {n}.", ["conclusion", "theme", "recur"], ["memory"]),
    ("Describe industry evolution stored in {n} research memory.", ["industry", "evolution", "memory"], ["memory"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _mem_prompts:
        _add("research_memory", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section H — Cross-Document Intelligence (50) ----
_xd_prompts = [
    ("Connect annual reports, transcripts, and presentations for {n}.", ["annual", "transcript", "presentation", "document"], ["cross_document"]),
    ("Explain cross-document intelligence for {n}.", ["cross", "document"], ["cross_document"]),
    ("Compare FY23/FY24 annual report chain with earnings transcripts for {n}.", ["annual", "transcript", "document", "fy"], ["cross_document", "annual_report"]),
    ("Build one document timeline for {n} including investor day / presentations.", ["timeline", "document", "presentation"], ["cross_document"]),
    ("How do filings, press releases, and research notes link for {n}?", ["filing", "press", "research", "document"], ["cross_document"]),
    ("Describe document linkage across Q1/Q2 earnings and annual reports for {n}.", ["document", "linkage", "annual", "earnings"], ["cross_document"]),
    ("What document types are in the {n} research workspace?", ["document", "annual", "transcript"], ["cross_document"]),
    ("Synthesize cross-document chronology for {n}.", ["document", "chronolog", "timeline"], ["cross_document", "timeline"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _xd_prompts:
        _add("cross_document", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section I — Timeline Intelligence (30) ----
_tl_prompts = [
    ("Build the research timeline for {n}.", ["timeline", "chronolog", "event"], ["timeline"]),
    ("List major events on the {n} research timeline.", ["timeline", "event"], ["timeline"]),
    ("Map leadership and acquisition milestones for {n}.", ["timeline", "leadership", "acquisition"], ["timeline", "events"]),
    ("Explain capital allocation milestones on the {n} timeline.", ["timeline", "capital", "allocat"], ["timeline"]),
    ("What industry changes appear on the {n} chronological timeline?", ["timeline", "industry"], ["timeline"]),
    ("Provide chronological intelligence for {n} with no missing major categories.", ["timeline", "chronolog", "ipo", "history", "guidance", "strategy"], ["timeline"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _tl_prompts:
        _add("timeline", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section J — Deep Research (50) ----
_dr_prompts = [
    ("Summarize five years of strategy for {n}.", ["strategy", "five", "5y", "evolution"], ["deep_research"]),
    ("How has management changed / evolved for {n}?", ["management", "evolution"], ["deep_research", "management"]),
    ("Explain capital allocation evolution for {n}.", ["capital", "allocat", "evolution"], ["deep_research"]),
    ("Compare guidance vs delivery framing for {n}.", ["guidance", "accuracy", "delivery"], ["deep_research", "guidance"]),
    ("Compare business evolution for {n} across FY2022 vs FY2026.", ["fy2022", "fy2026", "business", "strategy"], ["deep_research"]),
    ("Explain recurring themes across {n} annual reports.", ["theme", "recur", "annual"], ["deep_research", "annual_report"]),
    ("Perform deep research on competitive and risk evolution for {n}.", ["competitive", "risk", "evolution", "deep"], ["deep_research"]),
    ("Synthesize institutional research on {n} across five to ten years.", ["capital", "evolution", "research", "10"], ["deep_research"]),
]
for key in ENTITY_KEYS:
    for tmpl, must, mods in _dr_prompts:
        _add("deep_research", tmpl.format(n=_n(key)), entity=key, must_any=must, expect_modules=mods)

# ---- Section K — Impossible Questions (20) ----
_impossible = [
    ("What will Reliance report next quarter?", "reliance", ["refuse", "forecast", "unknown", "no buy"], True),
    ("Will TCS beat expectations?", "tcs", ["refuse", "forecast", "unknown", "expectation"], True),
    ("Will margins increase for HDFC Bank?", "hdfc_bank", ["refuse", "forecast", "unknown", "margin"], True),
    ("Will Infosys outperform next year?", "infosys", ["refuse", "forecast", "unknown"], True),
    ("Predict Asian Paints' next earnings print.", "asian_paints", ["refuse", "forecast", "unknown", "predict"], True),
    ("What will TCS revenue be next quarter?", "tcs", ["refuse", "forecast", "unknown"], True),
    ("Will Reliance earnings grow next quarter?", "reliance", ["refuse", "forecast", "unknown"], True),
    ("Forecast HDFC Bank NIM next year.", "hdfc_bank", ["refuse", "forecast", "unknown"], True),
    ("Will Infosys margins expand next quarter?", "infosys", ["refuse", "forecast", "margin", "unknown"], True),
    ("Predict Asian Paints volume growth next quarter.", "asian_paints", ["refuse", "forecast", "unknown"], True),
    ("BUY or SELL Reliance?", "reliance", ["no buy", "no sell", "recommend", "policy"], True),
    ("Should I buy TCS?", "tcs", ["no buy", "recommend", "policy", "refuse"], True),
    ("Target price for Infosys?", "infosys", ["target", "policy", "no buy", "refuse"], True),
    ("Give me a price target for HDFC Bank.", "hdfc_bank", ["target", "price", "policy", "refuse"], True),
    ("Is Asian Paints a buy right now?", "asian_paints", ["no buy", "policy", "refuse"], True),
    ("Should I sell Reliance this week?", "reliance", ["no sell", "no buy", "policy", "refuse"], True),
    ("Rate TCS overweight or underweight.", "tcs", ["policy", "refuse", "recommend", "no buy"], True),
    ("Is Infosys a sell?", "infosys", ["no sell", "policy", "refuse"], True),
    ("Provide a BUY rating for HDFC Bank.", "hdfc_bank", ["no buy", "policy", "refuse"], True),
    ("What is the target price and buy recommendation for Asian Paints?", "asian_paints", ["target", "no buy", "policy", "refuse"], True),
]
for prompt, entity, must, refuse in _impossible:
    _add(
        "impossible",
        prompt,
        entity=entity,
        must_any=must,
        policy_refuse=refuse,
        expect_modules=["policy"],
        fields_any=["summary", "unknowns"],
    )

# Enforce exact 400 — trim/pad if section math drifts
assert len(RI_ACCEPTANCE_400) == 400, len(RI_ACCEPTANCE_400)
for i, case in enumerate(RI_ACCEPTANCE_400, 1):
    case["id"] = f"RIA-{i:03d}"


def _blob(payload: Dict[str, Any]) -> str:
    parts = [
        payload.get("executive_summary") or payload.get("summary"),
        " ".join(payload.get("whats_new") or []),
        payload.get("business_impact") or "",
        payload.get("financial_impact") or "",
        payload.get("industry_impact") or "",
        payload.get("investment_implications") or "",
        " ".join(payload.get("unknowns") or []),
        " ".join(payload.get("monitoring_points") or []),
        payload.get("recommendation_policy") or "",
        payload.get("refuse_kind") or "",
        " ".join(payload.get("modules_used") or []),
    ]
    for key in (
        "research_object",
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
        "evidence",
    ):
        block = payload.get(key)
        if isinstance(block, dict):
            parts.append(block.get("summary") or "")
            parts.append(str(block)[:3500])
        elif block:
            parts.append(str(block)[:1500])
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_ri_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    text = _blob(payload)
    summary = (payload.get("executive_summary") or payload.get("summary") or "").strip()
    must = case.get("must_any") or []
    hits = sum(1 for m in must if m.lower() in text)
    modules = [str(m).lower() for m in (payload.get("modules_used") or [])]
    expect_mods = [str(m).lower() for m in (case.get("expect_modules") or [])]

    fields = case.get("fields_any") or []
    field_ok = (not fields) or any(
        payload.get(f)
        or (isinstance(payload.get(f), dict) and payload[f])
        or (isinstance(payload.get(f), list) and payload[f])
        or (f == "summary" and summary)
        for f in fields
    )
    direct_first = bool(summary) and len(summary) > 24 and not summary.lower().startswith(
        ("analyse via", "framework", "intent:", "planning:")
    )
    no_fabricated = payload.get("fabricated") is not True
    no_reco = payload.get("recommendation") in (None, "", "none") and not has_recommendation_leak(summary)
    policy_ok = "no_buy_sell" in str(payload.get("recommendation_policy") or "") or "observations_only" in str(
        payload.get("recommendation_policy") or ""
    )
    no_framework = not summary.lower().startswith(("analyse via", "framework", "intent:", "planning:"))

    entity_ok = True
    wrong_company = False
    if case.get("entity") and not case.get("policy_refuse"):
        name = CORPUS[case["entity"]]["name"].split()[0].lower()
        entity_ok = name in text or case["entity"].replace("_", " ") in text or "research" in text
        # Entity substitution: another corpus name dominates while expected is absent
        others = [
            CORPUS[k]["name"].split()[0].lower()
            for k in CORPUS
            if k != case["entity"]
        ]
        if name not in text and any(o in text for o in others):
            wrong_company = True
            entity_ok = False

    # Planner / module accuracy
    module_ok = True
    if expect_mods and not case.get("policy_refuse"):
        module_ok = any(m in modules or m in text for m in expect_mods)
    if case.get("policy_refuse"):
        module_ok = bool(payload.get("policy_refuse")) or any(
            m in modules for m in ("refuse_forecast", "refuse_recommendation", "policy")
        )

    # Research memory leakage / invented quotes
    memory_leak = any(
        bad in summary.lower()
        for bad in ("invented quote", "as the ceo said verbatim", "fabricated transcript")
    )
    no_memory_leak = not memory_leak

    # Hallucination signals (automatic fail)
    halluc = (
        (not no_fabricated)
        or wrong_company
        or any(
            bad in summary.lower()
            for bad in (
                "invented guidance",
                "as quoted invent",
                "fabricated event",
                "i made up",
            )
        )
    )

    need = 1 if len(must) <= 2 else min(2, len(must))
    topic_ok = hits >= need
    if case.get("policy_refuse"):
        topic_ok = topic_ok and bool(payload.get("policy_refuse"))

    # Weighted scoring components (for report aggregation)
    scores = {
        "research_accuracy": 1.0 if topic_ok and entity_ok and not halluc else 0.0,
        "document_understanding": 1.0 if module_ok and field_ok else 0.0,
        "cross_document_reasoning": 1.0
        if (case.get("section") not in {"cross_document", "deep_research"} or topic_ok)
        else 0.0,
        "research_memory": 1.0 if no_memory_leak and (case.get("section") != "research_memory" or topic_ok) else 0.0,
        "evidence_quality": 1.0 if (payload.get("evidence") or case.get("policy_refuse")) and no_fabricated else 0.0,
        "executive_communication": 1.0 if direct_first and no_framework else 0.0,
        "uncertainty": 1.0 if (payload.get("unknowns") or case.get("policy_refuse")) else 0.0,
    }
    weighted = (
        0.30 * scores["research_accuracy"]
        + 0.20 * scores["document_understanding"]
        + 0.15 * scores["cross_document_reasoning"]
        + 0.10 * scores["research_memory"]
        + 0.10 * scores["evidence_quality"]
        + 0.10 * scores["executive_communication"]
        + 0.05 * scores["uncertainty"]
    )

    hard_fail = (
        halluc
        or (not no_reco)
        or (not policy_ok)
        or (not no_framework)
        or (not no_memory_leak)
        or (payload.get("ok") is False and not case.get("policy_refuse"))
        or (case.get("policy_refuse") and not payload.get("policy_refuse"))
    )
    passed = (not hard_fail) and topic_ok and field_ok and direct_first and entity_ok and module_ok

    return {
        "id": case["id"],
        "section": case.get("section"),
        "category": case.get("category"),
        "prompt": case["prompt"],
        "pass": passed,
        "topic_hits": hits,
        "must_any": must,
        "field_ok": field_ok,
        "direct_answer_first": direct_first,
        "no_fabrication": no_fabricated,
        "hallucination": halluc,
        "no_recommendation_leakage": no_reco and policy_ok,
        "no_memory_leakage": no_memory_leak,
        "planner_module_ok": module_ok,
        "entity_ok": entity_ok,
        "weighted_score": round(100.0 * weighted, 2),
        "component_scores": scores,
        "summary": summary[:240],
        "modules_used": payload.get("modules_used") or [],
        "failed_assertions": [
            k
            for k, v in {
                "topic_ok": topic_ok,
                "field_ok": field_ok,
                "direct_first": direct_first,
                "no_fabricated": no_fabricated,
                "no_hallucination": not halluc,
                "no_reco": no_reco and policy_ok,
                "no_memory_leak": no_memory_leak,
                "entity_ok": entity_ok,
                "module_ok": module_ok,
                "hard_fail": not hard_fail,
            }.items()
            if not v
        ],
    }
