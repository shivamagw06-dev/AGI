"""Phase 3.0 orchestrator — plans which BI modules to run (no Ask wiring)."""

from __future__ import annotations

import re
from typing import Any, Optional

from business_intelligence.foundation.comparison import compare_companies
from business_intelligence.foundation.engines import (
    analyse_business_model,
    analyse_growth,
    analyse_industry,
    analyse_lifecycle,
    analyse_management,
    analyse_moat,
    analyse_risks,
    analyse_unit_economics,
    analyse_value_drivers,
)
from business_intelligence.foundation.evidence import assemble_evidence
from business_intelligence.foundation.graph import build_knowledge_graph
from business_intelligence.foundation.schema import BusinessIntelligencePackage

_INTENT_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "comparison",
        re.compile(
            r"\b(compare|vs\.?|versus|more profitable than|higher margins than|"
            r"better margins than)\b",
            re.I,
        ),
    ),
    (
        "moat",
        re.compile(
            r"\b(moat|competitive advantage|pricing power|premium pricing|"
            r"sustain premium|switching costs?|network effects?|"
            r"scale advantages?|customer lock[- ]?in|licensing moat|distribution moat|"
            r"brand moat|lock-in)\b",
            re.I,
        ),
    ),
    ("unit_economics", re.compile(r"\b(unit economics|contribution margin|cac|ltv|payback)\b", re.I)),
    (
        "value_drivers",
        re.compile(
            r"\b(value drivers?|what drives|nim|casa|nrr|load factor|arpob|utilization|"
            r"capital intensity|working capital profile|operating leverage)\b",
            re.I,
        ),
    ),
    (
        "industry",
        re.compile(
            r"\b(porter|five forces|industry structure|industry concentration|"
            r"entry barriers?|supplier power|customer power|competitive rivalry|substitutes?)\b",
            re.I,
        ),
    ),
    (
        "growth",
        re.compile(
            r"\b(growth|expansion|cross-sell(?:ing)?|upsell(?:ing)?|capacity expansion|"
            r"market share|mix improvement|pricing-led|volume-led|organic vs)\b",
            re.I,
        ),
    ),
    (
        "management",
        re.compile(
            r"\b(management quality|capital allocation|governance|shareholder friendl|"
            r"return discipline|strategic consistency|acquisition history|"
            r"management execution|score shareholder)\b",
            re.I,
        ),
    ),
    (
        "risks",
        re.compile(
            r"\b(risks?|disruption|concentration risk|refinanc\w*|regulatory risk|"
            r"commodity risk|business risks?)\b",
            re.I,
        ),
    ),
    ("lifecycle", re.compile(r"\b(lifecycle|life cycle|hypergrowth|turnaround|mature|decline|cyclical recovery)\b", re.I)),
    ("graph", re.compile(r"\b(suppliers?|customers?|competitors?|value chain|ecosystem)\b", re.I)),
    (
        "business_model",
        re.compile(
            r"\b(business model|membership model|how does .+ make money|"
            r"revenue stream|monetis|monetiz|cost advantages?)\b",
            re.I,
        ),
    ),
]


def detect_intents(question: str) -> list[str]:
    intents: list[str] = []
    for name, rx in _INTENT_RULES:
        if rx.search(question or ""):
            intents.append(name)
    if not intents:
        intents = ["business_model", "value_drivers"]
    # Always enrich company questions with model + moat lightly when company-bound later.
    return intents


def analyse(
    question: str,
    *,
    ticker: Optional[str] = None,
    industry_hint: Optional[str] = None,
) -> dict[str, Any]:
    intents = detect_intents(question)
    ev = assemble_evidence(question, ticker=ticker, industry_hint=industry_hint)

    modules_used: list[str] = []
    pkg = BusinessIntelligencePackage(
        ok=True,
        question=question,
        company=(ev.get("company") or {}).get("company_name"),
        ticker=ev.get("ticker"),
        industry=ev.get("industry_key"),
        modules_used=modules_used,
        evidence=list(ev.get("evidence") or []),
        fabricated=False,
    )

    why: list[str] = []
    summary_parts: list[str] = []

    if "comparison" in intents:
        comp = compare_companies(question)
        pkg.comparison = comp
        modules_used.append("comparison")
        summary_parts.append(comp.get("summary") or "")
        why.append("Comparison uses business axes (model, moat, growth, capital intensity), not ratios alone.")

    # Concept-first modules: prefer their summaries over company blurbs.
    concept_priority = ("moat", "risks", "management", "growth", "lifecycle", "unit_economics", "value_drivers", "industry")

    if "business_model" in intents or (
        ev.get("ticker") and "comparison" not in intents and not any(i in intents for i in concept_priority)
    ):
        bm = analyse_business_model(ev)
        pkg.business_model = bm
        modules_used.append("business_model")
        summary_parts.append(bm.get("how_it_makes_money") or "")
        why.append(f"Business type: {bm.get('business_type')}.")

    if "value_drivers" in intents or "business_model" in intents:
        vd = analyse_value_drivers(ev)
        pkg.value_drivers = vd
        modules_used.append("value_drivers")
        # Named company pedagogy / business-model answers must lead — never let
        # a generic "For retail, enterprise value is primarily driven by…" card
        # overwrite Costco/Apple/Reliance how-it-makes-money prose.
        named_lead = bool(summary_parts and not str(summary_parts[0]).lower().startswith("for "))
        if "value_drivers" in intents and "business_model" not in intents and not named_lead:
            summary_parts.insert(0, vd.get("summary") or "")
        elif "value_drivers" in intents and not named_lead and not summary_parts:
            summary_parts.insert(0, vd.get("summary") or "")
        why.append(vd.get("summary") or "")

    if "unit_economics" in intents:
        ue = analyse_unit_economics(ev)
        pkg.unit_economics = ue
        modules_used.append("unit_economics")
        summary_parts.insert(0, ue.get("summary") or "")

    if "moat" in intents or (
        ev.get("ticker") and "comparison" not in intents and "business_model" in intents
    ):
        moat = analyse_moat(ev)
        pkg.moat = moat
        modules_used.append("moat")
        if "moat" in intents:
            summary_parts.insert(0, moat.get("summary") or "")
        why.append(moat.get("summary") or "")

    if "industry" in intents or "value_drivers" in intents:
        ind = analyse_industry(ev)
        pkg.industry_structure = ind
        modules_used.append("industry")
        if "industry" in intents:
            summary_parts.insert(0, ind.get("summary") or "")
        why.append(ind.get("summary") or "")

    if "growth" in intents:
        gr = analyse_growth(ev)
        pkg.growth = gr
        modules_used.append("growth")
        summary_parts.insert(0, gr.get("summary") or "")
        why.append(gr.get("summary") or "")

    if "management" in intents:
        mg = analyse_management(ev)
        pkg.management = mg
        modules_used.append("management")
        summary_parts.insert(0, mg.get("summary") or "")
        why.append(mg.get("summary") or "")

    # Full IC / research memoranda list "risks" as a section — keep risk in why,
    # but never let a risk dump overwrite the business-model lead.
    ic_shaped = any(
        k in (question or "").lower()
        for k in (
            "investment committee",
            "research memorandum",
            "committee memorandum",
            "as if you were",
            "dossier",
            "monitoring points",
        )
    )

    if "risks" in intents:
        rk = analyse_risks(ev)
        pkg.risks = rk
        modules_used.append("risks")
        if ic_shaped or "business_model" in intents:
            why.append(rk.get("summary") or "")
        else:
            summary_parts.insert(0, rk.get("summary") or "")
            why.append(rk.get("summary") or "")

    if "lifecycle" in intents:
        lc = analyse_lifecycle(ev)
        pkg.lifecycle = lc
        modules_used.append("lifecycle")
        if ic_shaped or "business_model" in intents:
            why.append(lc.get("summary") or "")
        else:
            summary_parts.insert(0, lc.get("summary") or "")
            why.append(lc.get("summary") or "")

    if "graph" in intents or (ev.get("ticker") and "business_model" in modules_used):
        kg = build_knowledge_graph(ev)
        pkg.knowledge_graph = kg
        modules_used.append("knowledge_graph")

    # Dedup modules preserving order
    seen = set()
    pkg.modules_used = [m for m in modules_used if not (m in seen or seen.add(m))]

    # Prefer direct answer first: business model how-money, else comparison, else value drivers.
    # Never headline with a pure risk dump when a business description exists.
    summary = ""
    preferred = [
        p for p in summary_parts
        if p and p.strip() and not str(p).lower().startswith("primary business risks")
    ]
    for part in preferred or summary_parts:
        if part and part.strip():
            summary = part.strip()
            break
    if not summary:
        summary = why[0] if why else "Insufficient business evidence for a structured conclusion."
    pkg.summary = summary[:900]
    pkg.why = [w for w in why if w][:10]
    confs = []
    for block in (
        pkg.business_model,
        pkg.moat,
        pkg.value_drivers,
        pkg.industry_structure,
        pkg.comparison,
        pkg.unit_economics,
    ):
        if isinstance(block, dict) and block.get("confidence") is not None:
            confs.append(float(block["confidence"]))
    pkg.confidence = max(confs) if confs else 0.4
    pkg.ok = bool(pkg.summary)
    return pkg.to_dict()
