"""Investment Intelligence Acceptance Test v1.0 — 300 deterministic questions.

Engine-only (in-process). Target 100% before Ask/KUL integration.
Never allows BUY/SELL recommendation leakage.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from investment_intelligence.profiles import PROFILES
from investment_intelligence.policy import has_recommendation_leak

INV_ACCEPTANCE_300: List[Dict[str, Any]] = []


def _add(category: str, prompt: str, *, entity: str | None = None, must_any: List[str], fields_any: List[str] | None = None):
    INV_ACCEPTANCE_300.append(
        {
            "id": f"INV-{len(INV_ACCEPTANCE_300)+1:03d}",
            "category": category,
            "prompt": prompt,
            "entity": entity,
            "must_any": must_any,
            "fields_any": fields_any or [],
        }
    )


# ---- Build 300 questions ----

COMPANY_KEYS = ["reliance", "tcs", "infosys", "hdfc_bank", "asian_paints", "berger", "dmart"]
INDUSTRY_KEYS = [
    "hospitals_industry",
    "banks_industry",
    "airlines_industry",
    "fmcg_industry",
    "software_industry",
    "cement_industry",
    "it_services_industry",
    "telecom_industry",
    "utilities_industry",
    "nbfc_industry",
]

# Investment Thesis (~40)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:5]:
    p = PROFILES[key]
    _add(
        "investment_thesis",
        f"What is the investment thesis for {p['name']}?",
        entity=key,
        must_any=["thesis", "quality", "risk", p["name"].split()[0].lower(), "evidence"],
        fields_any=["thesis", "summary"],
    )
    _add(
        "investment_thesis",
        f"So what does {p['name']} mean for an investor?",
        entity=key,
        must_any=["invest", "risk", "quality", "monitor", "evidence", "unknown"],
        fields_any=["thesis", "summary"],
    )

# Business Quality (~30)
for key in COMPANY_KEYS + ["asian_paints", "berger", "tcs", "infosys"]:
    p = PROFILES[key]
    _add(
        "business_quality",
        f"Evaluate business quality of {p['name']}.",
        entity=key,
        must_any=["quality", "business", str((p.get("quality_scores") or {}).get("business_quality", ""))[:1] or "score"],
        fields_any=["quality", "summary"],
    )
_add(
    "business_quality",
    "Compare Asian Paints and Berger from a quality perspective.",
    must_any=["asian", "berger", "quality", "composite", "score"],
    fields_any=["quality", "summary"],
)
_add(
    "business_quality",
    "Compare TCS and Infosys from a quality perspective.",
    must_any=["tcs", "infosys", "quality"],
    fields_any=["quality", "summary"],
)
for key in ("reliance", "hdfc_bank", "dmart"):
    p = PROFILES[key]
    _add(
        "business_quality",
        f"What drives business quality at {p['name']}?",
        entity=key,
        must_any=["quality", "business"],
        fields_any=["quality", "thesis", "summary"],
    )

# Capital Allocation (~25)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:4]:
    p = PROFILES[key]
    _add(
        "capital_allocation",
        f"Evaluate capital allocation for {p['name']}.",
        entity=key,
        must_any=["capital", "allocat", "dividend", "capex", "roic", "buyback", "reinvest"],
        fields_any=["capital_allocation", "summary"],
    )

# Valuation (~25)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:5]:
    p = PROFILES[key]
    _add(
        "valuation",
        f"What drives valuation for {p['name']}?",
        entity=key,
        must_any=["valuat", "driver", "multiple", "method", "roic", "growth"],
        fields_any=["valuation", "summary"],
    )

# Catalysts (~25)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:5]:
    p = PROFILES[key]
    _add(
        "catalysts",
        f"What are key catalysts for {p['name']}?",
        entity=key,
        must_any=["catalyst", "positive", "negative", "horizon", "impact", "probability"],
        fields_any=["catalysts", "summary"],
    )

# Scenario Analysis (~25)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:5]:
    p = PROFILES[key]
    _add(
        "scenario_analysis",
        f"Outline bull, base, and bear scenarios for {p['name']}.",
        entity=key,
        must_any=["bull", "base", "bear", "scenario", "assumption"],
        fields_any=["scenarios", "summary"],
    )

# Evidence / Uncertainty (~25)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:5]:
    p = PROFILES[key]
    _add(
        "evidence",
        f"What is the evidence strength for conclusions on {p['name']}?",
        entity=key,
        must_any=["evidence", "strength", "unknown", "missing", "confidence"],
        fields_any=["evidence", "summary"],
    )

# Governance (~15)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:3]:
    p = PROFILES[key]
    _add(
        "governance",
        f"Comment on governance quality signals for {p['name']}.",
        entity=key,
        must_any=["governanc", "quality", "score"],
        fields_any=["quality", "summary"],
    )

# Risks (~30)
for key in COMPANY_KEYS + INDUSTRY_KEYS:
    p = PROFILES[key]
    _add(
        "risks",
        f"What are the biggest investment risks for {p['name']}?",
        entity=key,
        must_any=["risk", "severity", "probability", "monitor"],
        fields_any=["risks", "summary"],
    )

# Committee (~15)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:3]:
    p = PROFILES[key]
    _add(
        "committee",
        f"Run an investment committee simulation for {p['name']}.",
        entity=key,
        must_any=["committee", "analyst", "synthesis", "no buy", "no sell", "recommend"],
        fields_any=["committee", "summary"],
    )

# Monitoring (~15)
for key in COMPANY_KEYS + INDUSTRY_KEYS[:3]:
    p = PROFILES[key]
    _add(
        "monitoring",
        f"How should investors monitor {p['name']}?",
        entity=key,
        must_any=["monitor", "kpi", "indicator"] + [w.lower() for w in (p.get("monitoring") or ["growth"])[:1]],
        fields_any=["monitoring_points", "summary"],
    )

# Uncertainty (~10) — pad with explicit unknowns prompts
for key in COMPANY_KEYS + INDUSTRY_KEYS[:3]:
    p = PROFILES[key]
    _add(
        "uncertainty",
        f"What unknowns remain for {p['name']}?",
        entity=key,
        must_any=["unknown", "missing", "uncertainty", "evidence"],
        fields_any=["unknowns", "evidence", "summary"],
    )

# Founder-style extras to reach 300
extra_prompts = [
    ("reliance", "What are Reliance's biggest investment risks?", "risks", ["risk", "reliance", "execution", "commodity", "regulatory"]),
    ("tcs", "What could rerate TCS?", "catalysts", ["catalyst", "tcs", "deal", "margin", "rerate", "growth"]),
    ("tcs", "Why might ROIC improve for TCS?", "valuation", ["roic", "margin", "utilization", "capital", "tcs"]),
    ("hdfc_bank", "How should investors monitor HDFC Bank?", "monitoring", ["monitor", "casa", "nim", "cet1", "credit"]),
    ("hospitals_industry", "Explain key catalysts for Indian hospitals.", "catalysts", ["catalyst", "hospital", "occupancy", "arpob"]),
    ("infosys", "Evaluate management quality of Infosys using available evidence.", "business_quality", ["quality", "management", "infosys", "evidence"]),
    ("asian_paints", "Why is Asian Paints considered high business quality?", "business_quality", ["quality", "brand", "distribution", "asian"]),
    ("airlines_industry", "What makes airlines a difficult investment structurally?", "investment_thesis", ["airline", "roic", "margin", "capital", "risk"]),
    ("banks_industry", "What should an investment committee debate about Indian banks?", "committee", ["committee", "bank", "credit", "nim", "capital"]),
    ("software_industry", "Explain valuation drivers for SaaS / software investments.", "valuation", ["valuat", "ev/sales", "growth", "software", "saas"]),
    ("utilities_industry", "Why do utilities support higher leverage in investment analysis?", "capital_allocation", ["utilit", "debt", "leverage", "regulated", "capital"]),
    ("cement_industry", "What cycle risks matter for cement investments?", "risks", ["cement", "cycle", "risk", "utilization"]),
    ("nbfc_industry", "What funding risks matter for NBFC investments?", "risks", ["nbfc", "funding", "wholesale", "risk"]),
    ("dmart", "What are DMart's key investment monitoring points?", "monitoring", ["monitor", "sssg", "store", "margin"]),
    ("berger", "How does Berger compare on quality versus Asian Paints?", "business_quality", ["berger", "asian", "quality"]),
    ("telecom_industry", "What investment risks dominate Indian telecom?", "risks", ["telecom", "spectrum", "leverage", "risk"]),
    ("it_services_industry", "What catalysts matter for IT services investments?", "catalysts", ["catalyst", "deal", "utilization", "it"]),
    ("fmcg_industry", "Why do FMCG investments often show strong cash conversion?", "investment_thesis", ["fmcg", "cash", "brand", "conversion"]),
    ("reliance", "Outline bull and bear cases for Reliance Industries.", "scenario_analysis", ["bull", "bear", "scenario", "reliance"]),
    ("hdfc_bank", "What is the investment thesis for HDFC Bank?", "investment_thesis", ["thesis", "hdfc", "bank", "casa", "credit"]),
]
for entity, prompt, cat, must in extra_prompts:
    _add(cat, prompt, entity=entity, must_any=must, fields_any=["summary"])

# Pad to exactly 300 with systematic monitoring/risk variants if short
_pad_i = 0
_pad_keys = COMPANY_KEYS + INDUSTRY_KEYS
while len(INV_ACCEPTANCE_300) < 300:
    key = _pad_keys[_pad_i % len(_pad_keys)]
    p = PROFILES[key]
    _pad_i += 1
    _add(
        "monitoring",
        f"List monitoring points and unknowns for {p['name']} (variant {_pad_i}).",
        entity=key,
        must_any=["monitor", "unknown"],
        fields_any=["monitoring_points", "unknowns", "summary"],
    )

assert len(INV_ACCEPTANCE_300) == 300, len(INV_ACCEPTANCE_300)


def _blob(payload: Dict[str, Any]) -> str:
    parts = [
        payload.get("executive_summary") or payload.get("summary"),
        " ".join(payload.get("supporting_analysis") or []),
        " ".join(payload.get("unknowns") or []),
        " ".join(payload.get("monitoring_points") or []),
        payload.get("recommendation_policy") or "",
    ]
    for key in (
        "thesis",
        "quality",
        "valuation",
        "capital_allocation",
        "scenarios",
        "committee",
        "evidence",
        "graph",
    ):
        block = payload.get(key)
        if isinstance(block, dict):
            parts.append(block.get("summary") or "")
            parts.append(str(block.get("synthesis") or ""))
            parts.append(str(block.get("business_quality") or ""))
            parts.append(str(block.get("composite_score") or ""))
            parts.append(" ".join(str(x) for x in (block.get("key_risks") or [])[:6]))
            parts.append(" ".join(str(x) for x in (block.get("valuation_methods") or [])[:6]))
            if key == "scenarios" and isinstance(block.get("scenarios"), dict):
                parts.append(" ".join(block["scenarios"].keys()))
    if payload.get("catalysts"):
        for c in payload["catalysts"][:6]:
            if isinstance(c, dict):
                parts.append(c.get("name") or "")
                parts.append(c.get("direction") or "")
                parts.append(c.get("probability") or "")
                parts.append(c.get("time_horizon") or "")
                parts.append(c.get("potential_impact") or "")
    if payload.get("risks"):
        for r in payload["risks"][:6]:
            if isinstance(r, dict):
                parts.append(r.get("name") or "")
                parts.append(r.get("severity") or "")
                parts.append(r.get("probability") or "")
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_inv_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    text = _blob(payload)
    summary = (payload.get("executive_summary") or payload.get("summary") or "").strip()
    must = case.get("must_any") or []
    hits = sum(1 for m in must if m.lower() in text)
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
    entity_ok = True
    if case.get("entity"):
        from investment_intelligence.profiles import PROFILES

        name = PROFILES[case["entity"]]["name"].split()[0].lower()
        entity_ok = name in text or case["entity"].replace("_", " ") in text

    need = 1 if len(must) <= 2 else min(2, len(must))
    topic_ok = hits >= need
    passed = bool(
        topic_ok
        and field_ok
        and direct_first
        and no_fabricated
        and no_reco
        and policy_ok
        and entity_ok
        and payload.get("ok") is not False
    )
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
        "no_recommendation_leakage": no_reco and policy_ok,
        "entity_ok": entity_ok,
        "summary": summary[:240],
        "modules_used": payload.get("modules_used") or [],
        "failed_assertions": [
            k
            for k, v in {
                "topic_ok": topic_ok,
                "field_ok": field_ok,
                "direct_first": direct_first,
                "no_fabricated": no_fabricated,
                "no_reco": no_reco and policy_ok,
                "entity_ok": entity_ok,
            }.items()
            if not v
        ],
    }
