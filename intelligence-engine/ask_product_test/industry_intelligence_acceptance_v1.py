"""Industry Intelligence Acceptance Test v1.0 — 200 deterministic questions.

Engine-only (in-process). Target 100% before Ask/KUL integration.
Does not modify AGI Core v1.0.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from industry_intelligence.dna_catalog import INDUSTRY_DNA

II_ACCEPTANCE_200: List[Dict[str, Any]] = []


def _add(category: str, prompt: str, *, industry: str | None = None, must_any: List[str], fields_any: List[str] | None = None):
    II_ACCEPTANCE_200.append(
        {
            "id": f"II-{len(II_ACCEPTANCE_200)+1:03d}",
            "category": category,
            "prompt": prompt,
            "industry": industry,
            "must_any": must_any,
            "fields_any": fields_any or [],
        }
    )


# ---- Build 200 questions across categories ----

# Industry Economics (~30)
for key in ("banks", "software", "retail", "airlines", "hospitals", "fmcg", "telecom", "cement", "insurance", "utilities"):
    d = INDUSTRY_DNA[key]
    _add(
        "industry_economics",
        f"Explain {d.name} industry economics.",
        industry=key,
        must_any=[w.lower() for w in d.revenue_drivers[:2]] + [d.name.split()[0].lower()],
        fields_any=["economics", "dna"],
    )
    _add(
        "industry_economics",
        f"What drives margins in {d.name}?",
        industry=key,
        must_any=["margin"] + [w.lower().split()[0] for w in d.margin_drivers[:2]],
        fields_any=["economics"],
    )
    _add(
        "industry_economics",
        f"Why is capital intensity important in {d.name}?",
        industry=key,
        must_any=["capital"],
        fields_any=["economics", "dna"],
    )

# KPIs (~40) — industry-specific
kpi_prompts = [
    ("banks", "What is CASA and why does it matter for banks?", ["casa", "deposit", "funding", "nim"]),
    ("banks", "Explain NIM for banks.", ["nim", "interest", "margin", "spread"]),
    ("banks", "What is CET1?", ["cet1", "capital", "solvency", "rwa"]),
    ("banks", "Explain GNPA and credit cost for banks.", ["gnpa", "npa", "credit", "provision"]),
    ("hospitals", "What is ARPOB?", ["arpob", "bed", "revenue", "occupancy"]),
    ("hospitals", "Explain hospital occupancy and ALOS.", ["occupancy", "alos", "bed", "length"]),
    ("airlines", "What is load factor for airlines?", ["load", "factor", "seat", "passenger"]),
    ("airlines", "Explain RASK and CASK.", ["rask", "cask", "yield", "cost"]),
    ("retail", "What is SSSG in retail?", ["same", "store", "sssg", "growth"]),
    ("retail", "Why do inventory days matter in retail?", ["inventory", "days", "working", "shrink"]),
    ("it_services", "Explain utilization in IT services.", ["utilization", "billable", "bench"]),
    ("it_services", "Why does attrition matter for IT companies?", ["attrition", "talent", "wage", "employee"]),
    ("it_services", "What is offshore mix?", ["offshore", "mix", "margin"]),
    ("software", "What is NRR for SaaS?", ["nrr", "retention", "expansion", "churn"]),
    ("software", "Explain CAC payback in software.", ["cac", "payback", "acquisition"]),
    ("telecom", "What is ARPU in telecom?", ["arpu", "revenue", "subscriber", "user"]),
    ("insurance", "Explain VNB margin.", ["vnb", "margin", "new business", "embedded"]),
    ("insurance", "What is persistency in insurance?", ["persistency", "policy", "force"]),
    ("nbfc", "What is spread for NBFCs?", ["spread", "yield", "funding", "cost"]),
    ("fmcg", "What drives FMCG gross margin?", ["margin", "brand", "mix", "commodity"]),
    ("automobile", "What is ASP in automobiles?", ["asp", "price", "mix", "volume"]),
    ("cement", "Why does utilization matter in cement?", ["utilization", "capacity", "fixed"]),
    ("pharma", "What is important in pharma KPIs?", ["pipeline", "anda", "margin", "rd", "r&d"]),
    ("real_estate", "What is pre-sales in real estate?", ["pre-sales", "presales", "booking", "collection"]),
    ("qsr", "What is SSSG for QSR?", ["same", "store", "sssg", "traffic"]),
    ("logistics", "Explain utilization in logistics.", ["utilization", "fleet", "network"]),
    ("metals", "What is realization in metals?", ["realization", "spread", "price", "cost"]),
    ("power", "What is PLF in power generation?", ["plf", "plant", "load", "factor"]),
    ("renewables", "What is CUF in renewables?", ["cuf", "capacity", "utilization"]),
    ("utilities", "What are AT&C losses?", ["at&c", "atc", "loss", "distribution"]),
    ("oil_gas", "What is GRM in oil & gas refining?", ["grm", "refining", "margin", "crack"]),
    ("asset_management", "What are net flows for AMCs?", ["flow", "aum", "inflow"]),
    ("data_centers", "What is utilization in data centers?", ["utilization", "power", "mw", "rack"]),
    ("internet_platforms", "What is take rate for platforms?", ["take", "rate", "gmv", "commission"]),
    ("hotels", "What is RevPAR?", ["revpar", "adr", "occupancy", "room"]),
    ("shipping", "What is freight rate importance in shipping?", ["freight", "rate", "spot", "charter"]),
    ("mining", "Why does grade matter in mining?", ["grade", "ore", "cost", "volume"]),
    ("chemicals", "What drives chemical spreads?", ["spread", "feedstock", "margin"]),
    ("diagnostics", "What matters for diagnostics KPIs?", ["test", "volume", "realization", "lab"]),
    ("education", "What is enrolments importance in education?", ["enrol", "student", "fee", "retention"]),
]

for industry, prompt, must in kpi_prompts:
    _add("kpis", prompt, industry=industry, must_any=must, fields_any=["kpis", "dna", "summary"])

# Valuation (~25)
val_cases = [
    ("banks", "Why do banks use P/B?", ["p/b", "book", "equity", "roe"]),
    ("software", "Why do SaaS companies trade on EV/Sales?", ["ev/sales", "sales", "arr", "revenue"]),
    ("insurance", "Why use Embedded Value for insurance?", ["embedded", "vnb", "in-force", "force"]),
    ("telecom", "Why do telecoms use EV/EBITDA?", ["ev/ebitda", "ebitda", "spectrum", "depreciation"]),
    ("utilities", "How are utilities typically valued?", ["dcf", "yield", "rab", "regulated"]),
    ("real_estate", "Why is NAV used for real estate?", ["nav", "asset", "propert"]),
    ("metals", "How are commodity companies valued?", ["ev/ebitda", "replacement", "cycle", "ebitda"]),
    ("airlines", "How should airlines be valued carefully?", ["ev/ebitda", "cycle", "fleet", "lease", "ebitda"]),
    ("fmcg", "What valuation methods fit FMCG?", ["p/e", "ev/ebitda", "brand", "fcf"]),
    ("nbfc", "How are NBFCs valued?", ["p/b", "book", "roe"]),
    ("hospitals", "How are hospital companies valued?", ["ev/ebitda", "p/e", "bed", "ebitda"]),
    ("it_services", "How are IT services firms valued?", ["p/e", "ev/ebitda", "earnings"]),
    ("cement", "Valuation approach for cement?", ["ev/ebitda", "replacement", "cycle"]),
    ("pharma", "How is pharma typically valued?", ["p/e", "pipeline", "ev/ebitda"]),
    ("oil_gas", "Valuation methods for oil & gas?", ["ev/ebitda", "reserve", "replacement", "nav"]),
    ("power", "How to value power generators?", ["ev/ebitda", "ppa", "dcf"]),
    ("renewables", "Valuation for renewables?", ["dcf", "ev/ebitda", "cuf", "tariff"]),
    ("asset_management", "How are AMCs valued?", ["p/e", "aum", "fee"]),
    ("internet_platforms", "Platform valuation methods?", ["ev/sales", "gmv", "take rate", "p/e"]),
    ("hotels", "Hotel valuation methods?", ["ev/ebitda", "revpar", "replacement"]),
    ("logistics", "Logistics valuation?", ["ev/ebitda", "p/e"]),
    ("automobile", "Auto OEM valuation?", ["ev/ebitda", "p/e", "cycle"]),
    ("capital_goods", "Capital goods valuation?", ["ev/ebitda", "p/e", "order"]),
    ("infrastructure", "Infrastructure valuation?", ["dcf", "nav", "yield", "ev/ebitda"]),
    ("shipping", "Shipping valuation caveats?", ["ev/ebitda", "nav", "cycle", "freight"]),
]
for industry, prompt, must in val_cases:
    _add("valuation", prompt, industry=industry, must_any=must, fields_any=["valuation", "cross_industry", "summary"])

# Regulation (~20)
reg_cases = [
    ("banks", "Who regulates banks in India?", ["rbi"]),
    ("insurance", "Who regulates insurance?", ["irdai"]),
    ("telecom", "Who regulates telecom?", ["trai"]),
    ("airlines", "Who regulates airlines?", ["dgca"]),
    ("asset_management", "Who regulates mutual funds?", ["sebi"]),
    ("pharma", "What regulates drug pricing / pharma?", ["cdsco", "dpco", "nppa", "drug", "pricing"]),
    ("mining", "What are mining license risks?", ["license", "lease", "environmental", "regulatory"]),
    ("power", "Who oversees power sector regulation?", ["cea", "cerc", "serc", "electricity"]),
    ("utilities", "Regulatory risks for utilities?", ["tariff", "regulated", "at&c", "rab"]),
    ("capital_goods", "Any key regulation for capital goods?", ["standard", "project", "bid", "regulatory", "safety"]),
    ("real_estate", "Real estate regulatory framework?", ["rera"]),
    ("education", "Education regulation?", ["ugc", "aicte", "ncte", "regulatory", "affiliation", "aiu"]),
    ("nbfc", "Who regulates NBFCs?", ["rbi"]),
    ("oil_gas", "Oil & gas regulatory themes?", ["pngrb", "moPNG", "environmental", "subsidy", "pricing", "oil"]),
    ("renewables", "Renewables regulatory risks?", ["auction", "curtailment", "ppa", "discom"]),
    ("internet_platforms", "Platform regulatory risks?", ["data", "competition", "antitrust", "privacy"]),
    ("hospitals", "Hospital regulatory risks?", ["license", "clinical", "nursing", "ayushman", "pricing"]),
    ("chemicals", "Chemical regulatory risks?", ["environmental", "safety", "pollution"]),
    ("media", "Media regulation?", ["trai", "mib", "content", "license"]),
    ("data_centers", "Data center regulatory themes?", ["data", "localization", "power", "land"]),
]
for industry, prompt, must in reg_cases:
    _add("regulation", prompt, industry=industry, must_any=must, fields_any=["regulation", "summary"])

# Competition (~15)
for key in ("banks", "telecom", "airlines", "cement", "software", "retail", "internet_platforms", "steel" if False else "metals", "fmcg", "automobile", "hospitals", "qsr", "logistics", "pharma", "utilities"):
    d = INDUSTRY_DNA[key]
    _add(
        "competition",
        f"Describe competitive structure in {d.name}.",
        industry=key,
        must_any=[d.competitive_structure, "rivalry", "barrier", "entry", "oligopol", "fragment", "platform", "commodit"],
        fields_any=["competition"],
    )

# Cycles (~15)
for key in ("banks", "metals", "real_estate", "software", "cement", "automobile", "airlines", "shipping", "oil_gas", "hotels", "nbfc", "power", "chemicals", "capital_goods", "fmcg"):
    d = INDUSTRY_DNA[key]
    _add(
        "cycles",
        f"What cycle matters most for {d.name}?",
        industry=key,
        must_any=[d.primary_cycle.replace("_", " ").split()[0], "cycle"],
        fields_any=["cycle"],
    )

# Cash conversion / capital (~20)
for key in ("fmcg", "software", "banks", "airlines", "hospitals", "retail", "it_services", "utilities", "cement", "telecom", "insurance", "asset_management", "automobile", "metals", "real_estate", "qsr", "logistics", "pharma", "data_centers", "internet_platforms"):
    d = INDUSTRY_DNA[key]
    _add(
        "cash_conversion",
        f"Explain cash conversion in {d.name}.",
        industry=key,
        must_any=["cash", "working", "fcf", "receivable", "inventory", "float", "conversion"],
        fields_any=["economics", "dna"],
    )

# Capital allocation (~10)
for key in ("banks", "software", "fmcg", "airlines", "utilities", "it_services", "oil_gas", "real_estate", "pharma", "internet_platforms"):
    d = INDUSTRY_DNA[key]
    _add(
        "capital_allocation",
        f"What is typical capital allocation in {d.name}?",
        industry=key,
        must_any=["capital", "dividend", "reinvest", "capex", "buyback", "growth", "retain"],
        fields_any=["graph", "dna", "economics"],
    )

# Industry risks (~15)
for key in ("banks", "nbfc", "airlines", "software", "telecom", "pharma", "mining", "renewables", "hospitals", "real_estate", "metals", "oil_gas", "internet_platforms", "shipping", "agriculture"):
    d = INDUSTRY_DNA[key]
    _add(
        "industry_risks",
        f"What are the key risks in {d.name}?",
        industry=key,
        must_any=[w.lower().split()[0] for w in d.typical_risks[:3]] + ["risk"],
        fields_any=["risks"],
    )

# Cross industry (~10)
cross = [
    ("Why do banks use P/B?", ["book", "p/b", "equity", "spread", "roe"]),
    ("Why do SaaS companies trade on EV/Sales?", ["ev/sales", "sales", "arr", "growth", "fcf"]),
    ("Why do airlines earn low ROIC?", ["roic", "capital", "fleet", "load", "competition"]),
    ("Why do FMCG companies produce high FCF?", ["fcf", "cash", "brand", "working", "capex"]),
    ("Why do utilities carry more debt?", ["debt", "leverage", "regulated", "cash", "rab"]),
    ("Why do hospitals have higher working capital?", ["working", "receivable", "payer", "inventory", "insurer"]),
    ("Why do telecoms use EV/EBITDA?", ["ev/ebitda", "ebitda", "spectrum", "depreciation"]),
    ("Why is NAV used for real estate?", ["nav", "propert", "asset"]),
    ("Why use Embedded Value for insurers?", ["embedded", "vnb", "in-force", "force"]),
    ("Banks vs NBFCs — how do funding models differ?", ["deposit", "wholesale", "funding", "casa", "bank"]),
]
for prompt, must in cross:
    _add("cross_industry", prompt, must_any=must, fields_any=["cross_industry", "valuation", "economics", "summary"])

assert len(II_ACCEPTANCE_200) == 200, len(II_ACCEPTANCE_200)


def _blob(payload: Dict[str, Any]) -> str:
    parts = [
        payload.get("summary"),
        " ".join(payload.get("why") or []),
    ]
    for key in ("economics", "valuation", "regulation", "competition", "cycle", "risks", "graph", "cross_industry", "dna"):
        block = payload.get(key)
        if isinstance(block, dict):
            parts.append(block.get("summary") or "")
            parts.append(str(block.get("why") or ""))
            parts.append(str(block.get("why_margins") or ""))
            parts.append(str(block.get("valuation_why") or ""))
            parts.append(" ".join(str(x) for x in (block.get("regulators") or [])[:6]))
            parts.append(" ".join(str(x) for x in (block.get("valuation_methods") or [])[:6]))
            parts.append(str(block.get("competitive_structure") or ""))
            parts.append(str(block.get("primary_cycle") or ""))
            parts.append(" ".join(str(x) for x in (block.get("typical_risks") or [])[:6]))
            parts.append(str(block.get("cash_conversion") or ""))
            parts.append(str(block.get("working_capital") or ""))
            parts.append(str(block.get("capital_intensity") or ""))
            parts.append(str(block.get("capital_allocation_typical") or ""))
            parts.append(" ".join(str(x) for x in (block.get("revenue_drivers") or [])[:6]))
            parts.append(" ".join(str(x) for x in (block.get("margin_drivers") or [])[:6]))
            parts.append(" ".join(str(x) for x in (block.get("value_drivers") or [])[:6]))
            if isinstance(block.get("porter"), dict):
                parts.append(" ".join(str(x) for x in block["porter"].values()))
    if payload.get("kpis"):
        for k in payload["kpis"]:
            if isinstance(k, dict):
                parts.append(k.get("key") or "")
                parts.append(k.get("name") or "")
                parts.append(k.get("definition") or "")
                parts.append(k.get("importance") or "")
                parts.append(k.get("good_range") or "")
                parts.append(" ".join(k.get("relationships") or []))
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_ii_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    text = _blob(payload)
    summary = (payload.get("summary") or "").strip()
    must = case.get("must_any") or []
    hits = sum(1 for m in must if m.lower() in text)
    fields = case.get("fields_any") or []
    field_ok = (not fields) or any(
        payload.get(f)
        or (isinstance(payload.get(f), dict) and payload[f].get("found") is not False)
        or (f == "summary" and summary)
        for f in fields
    )
    direct_first = bool(summary) and len(summary) > 20 and not summary.lower().startswith(("analyse via", "framework", "intent:"))
    no_fabricated = payload.get("fabricated") is not True
    industry_ok = True
    if case.get("industry"):
        industry_ok = (payload.get("industry") == case["industry"]) or (case["industry"] in text)

    # Pass bar: at least 1 topic hit (or 2 if many musts), fields present, direct answer, no fabrication
    need = 1 if len(must) <= 2 else min(2, len(must))
    topic_ok = hits >= need
    passed = bool(topic_ok and field_ok and direct_first and no_fabricated and industry_ok and payload.get("ok") is not False)

    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "pass": passed,
        "topic_hits": hits,
        "must_any": must,
        "field_ok": field_ok,
        "direct_answer_first": direct_first,
        "no_fabrication": no_fabricated,
        "industry_ok": industry_ok,
        "summary": summary[:240],
        "modules_used": payload.get("modules_used") or [],
    }
