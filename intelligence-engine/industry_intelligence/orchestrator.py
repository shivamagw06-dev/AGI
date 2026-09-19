"""Intent detection and Industry Intelligence orchestration."""

from __future__ import annotations

import re
from typing import Any, Optional

from industry_intelligence import engines
from industry_intelligence.registry import resolve_industry
from industry_intelligence.schema import IndustryIntelligencePackage


def detect_intents(question: str) -> list[str]:
    q = (question or "").lower()
    intents: list[str] = []
    if re.search(
        r"\b(kpi|casa|nim|gnpa|nnpa|pcr|cet1|credit cost|arpob|occupancy|alos|"
        r"load factor|rask|cask|sssg|same[- ]store|utilization|attrition|billing rate|"
        r"offshore mix|nrr|cac|arpu|vnb|persistency|pre[- ]?sales|presales|revpar|"
        r"plf|cuf|grm|take rate|at&c|asp|freight rate|ore grade)\b",
        q,
    ):
        intents.append("kpis")
    if re.search(
        r"\b(valuat\w*|p/?b|price.to.book|ev/?sales|ev/?ebitda|ev/?ebitdar|"
        r"embedded value|\bnav\b|residual income|appraisal value)\b",
        q,
    ):
        intents.append("valuation")
    if re.search(
        r"\b(regulat\w*|regulator\w*|rbi|sebi|irdai|trai|dgca|npci|cea|nhai|"
        r"rera|ugc|aicte|cdsco|license\w*|spectrum|drug pricing|dpco|nppa)\b",
        q,
    ):
        intents.append("regulation")
    if re.search(
        r"\b(compet\w*|porter|oligopol\w*|duopol\w*|monopol\w*|fragmented|"
        r"entry barrier\w*|rivalry|supplier power|buyer power)\b",
        q,
    ):
        intents.append("competition")
    if re.search(
        r"\b(cycle|expansion|slowdown|recovery|credit cycle|commodity cycle|"
        r"housing cycle|interest rate cycle|technology cycle|cyclical)\b",
        q,
    ):
        intents.append("cycle")
    if re.search(r"\b(risk|risks)\b", q) and "regulat" not in q:
        intents.append("risks")
    elif re.search(r"\b(risk|risks)\b", q):
        # "regulatory risks" → regulation already added; also include risks
        intents.append("risks")
    if re.search(
        r"\b(customer|supplier|adjacent|value chain|industry graph|substitut\w*|"
        r"capital allocation)\b",
        q,
    ):
        intents.append("graph")
    if re.search(
        r"why do (banks|saas|software|airlines|fmcg|utilities|hospitals|telecoms?|"
        r"insurance|insurers?|commodity|real estate)\b|"
        r"why (do|does|is|are|use).{0,60}(p/?b|ev/?sales|ev/?ebitda|low roic|high fcf|"
        r"more debt|working capital|embedded value|\bnav\b)|"
        r"\bvs\.?\b|versus|compared to|difference between|funding models differ",
        q,
    ):
        intents.append("cross_industry")
    if re.search(
        r"\b(econom\w*|margin\w*|roic|capital intens\w*|working capital|cash conversion|"
        r"operating leverage|pricing power|revenue driver\w*|cost driver\w*|value driver\w*|"
        r"how .{0,40}industry work|industry dna|industry economics)\b",
        q,
    ):
        intents.append("economics")
    if not intents:
        intents.append("economics")
    # Dedup preserve order
    seen = set()
    out = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def analyse(
    question: str,
    *,
    industry: Optional[str] = None,
) -> dict[str, Any]:
    intents = detect_intents(question)
    key = industry or resolve_industry(question)
    modules: list[str] = []
    pkg = IndustryIntelligencePackage(ok=True, question=question, industry=key)
    why: list[str] = []
    summary = ""

    # Cross-industry can answer without a single bind
    if "cross_industry" in intents:
        cross = engines.cross_industry(question)
        pkg.cross_industry = cross
        modules.append("cross_industry")
        if cross.get("found") and cross.get("summary"):
            summary = cross["summary"]
            why.extend(list(cross.get("why") or []))
            if not key and cross.get("industry"):
                key = cross["industry"]
                pkg.industry = key

    if key:
        dna = engines.dna_view(key)
        pkg.dna = dna
        pkg.industry_name = dna.get("name")
        modules.append("dna")

        qlow = question.lower()

        # KPI scan even without explicit kpi intent (e.g. "What is CET1?")
        kpi_hint = None
        for card in dna.get("kpis") or []:
            key_l = card["key"].replace("_", " ")
            name_l = card["name"].lower()
            if key_l in qlow or name_l in qlow or card["key"].replace("_", "") in qlow.replace("-", "").replace(" ", ""):
                kpi_hint = card["key"]
                break
            # aliases in question tokens
            if any(tok and tok in qlow for tok in (card["key"], key_l, name_l.split()[0] if name_l else "")):
                if len(name_l.split()[0]) >= 3 and name_l.split()[0] in qlow:
                    kpi_hint = card["key"]
                    break
        # Common pedagogy aliases
        alias_kpi = {
            "cet1": "cet1",
            "pre-sales": "presales",
            "pre sales": "presales",
            "presales": "presales",
            "same store": "sssg",
            "sssg": "sssg",
            "at&c": "atc_losses",
            "atc": "atc_losses",
            "nrr": "nrr",
            "cac": "cac_payback",
            "asp": "asp",
            "freight": "tce",
            "grade": "grade",
        }
        for alias, kkey in alias_kpi.items():
            if alias in qlow:
                if any(c["key"] == kkey for c in (dna.get("kpis") or [])):
                    kpi_hint = kkey
                    break
                # soft match first kpi containing alias token
                soft = next((c["key"] for c in (dna.get("kpis") or []) if alias.replace(" ", "_") in c["key"] or alias in c["name"].lower()), None)
                if soft:
                    kpi_hint = soft
                    break
        if kpi_hint and "kpis" not in intents:
            intents.append("kpis")

        if "economics" in intents:
            eco = engines.economics(key)
            pkg.economics = eco
            modules.append("economics")
            if "capital intens" in qlow:
                summary = (
                    f"{dna.get('name')} capital intensity: {eco.get('capital_intensity')}. "
                    f"{eco.get('why_leverage') or ''}"
                ).strip()
            elif "cash conversion" in qlow:
                summary = (
                    f"{dna.get('name')} cash conversion: {eco.get('cash_conversion')}. "
                    f"Working capital: {eco.get('working_capital')}. "
                    f"{eco.get('why_working_capital') or ''}"
                ).strip()
            elif "working capital" in qlow:
                summary = (
                    f"{dna.get('name')} working capital: {eco.get('working_capital')}. "
                    f"{eco.get('why_working_capital') or ''}"
                ).strip()
            elif not summary:
                summary = eco.get("summary") or ""
            why.append(eco.get("why_margins") or "")
            why.append(eco.get("why_working_capital") or "")

        if "kpis" in intents:
            kp = engines.kpis(key, kpi_hint)
            pkg.kpis = kp.get("kpis") or ([kp["kpi"]] if kp.get("kpi") else None)
            modules.append("kpis")
            if not summary or kpi_hint:
                summary = kp.get("summary") or summary

        if "valuation" in intents:
            val = engines.valuation(key)
            pkg.valuation = val
            modules.append("valuation")
            if not summary or intents[0] in ("valuation", "cross_industry"):
                summary = val.get("summary") or summary
            why.append(val.get("why") or "")
            why.append(val.get("why_valuation") or "")

        if "regulation" in intents:
            reg = engines.regulation(key)
            pkg.regulation = reg
            modules.append("regulation")
            if intents[0] == "regulation" or not summary or "regulat" in qlow:
                summary = reg.get("summary") or summary

        if "competition" in intents:
            comp = engines.competition(key)
            pkg.competition = comp
            modules.append("competition")
            if intents[0] == "competition" or "compet" in qlow or not summary:
                summary = comp.get("summary") or summary

        if "cycle" in intents:
            cy = engines.cycle(key)
            pkg.cycle = cy
            modules.append("cycle")
            if intents[0] == "cycle" or "cycle" in qlow or not summary:
                summary = cy.get("summary") or summary

        if "risks" in intents:
            rk = engines.risks(key)
            pkg.risks = rk
            modules.append("risks")
            # Prefer regulation summary when the question is about regulatory risk
            if "regulat" not in qlow and (intents[0] == "risks" or not summary):
                summary = rk.get("summary") or summary

        if "graph" in intents or "capital allocation" in qlow:
            g = engines.graph(key)
            pkg.graph = g
            modules.append("graph")
            if "capital allocation" in qlow:
                summary = (
                    f"{dna.get('name')} typical capital allocation: "
                    f"{g.get('capital_allocation_typical')}"
                )
            elif intents[0] == "graph" or not summary:
                summary = g.get("summary") or summary

        if not summary and dna.get("found"):
            summary = (
                f"{dna.get('name')} Industry DNA: value drivers include "
                f"{', '.join((dna.get('value_drivers') or [])[:4])}; "
                f"valued using {', '.join((dna.get('valuation_methods') or [])[:2])}."
            )
            why.append(dna.get("why_valuation") or "")

    if not summary:
        summary = (
            "Industry Intelligence requires a supported industry (e.g. banks, hospitals, airlines, software). "
            "Ask about industry economics, KPIs, valuation methods, regulation, cycles, or risks."
        )
        pkg.ok = False
        pkg.confidence = 0.2
    else:
        pkg.ok = True
        pkg.confidence = 0.92 if key else 0.75

    # Prefer first intent's module summary already set; ensure direct answer first.
    pkg.summary = summary.strip()[:900]
    pkg.why = [w for w in why if w][:8]
    pkg.modules_used = []
    seen = set()
    for m in modules:
        if m not in seen:
            seen.add(m)
            pkg.modules_used.append(m)
    pkg.fabricated = False
    return pkg.to_dict()
