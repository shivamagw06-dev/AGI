"""Golden Business 20 — permanent business-intelligence regression suite.

Categories: Business Models, Moats, Competition, Unit Economics, Management,
Growth, Risks, Industry Structure.

Every future release should run this suite. Prefer Ask inprocess / live so the
product path is validated (not only the isolated BI engine).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ui.executive_composer import is_planning_scaffold
from app.ui.ticker_guard import looks_like_framework_meta_executive
from ask_product_test.founder_evaluation_v1 import HARD_FAIL_START_MARKERS

GOLDEN_BUSINESS_20: List[Dict[str, Any]] = [
    # Business Models (4)
    {
        "id": "GB20-BM01",
        "category": "Business Models",
        "prompt": "What is Reliance Industries' business model?",
        "expect": {
            "must_mention": ["reliance"],
            "topics_any": ["refin", "retail", "jio", "petro", "segment", "conglomerate"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-BM02",
        "category": "Business Models",
        "prompt": "Explain HDFC Bank's business model.",
        "expect": {
            "must_mention": ["hdfc"],
            "topics_any": ["bank", "deposit", "loan", "nim", "casa", "credit"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-BM03",
        "category": "Business Models",
        "prompt": "How does DMart make money?",
        "expect": {
            "must_mention": ["dmart"],
            "topics_any": ["retail", "store", "grocery", "margin", "volume"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-BM04",
        "category": "Business Models",
        "prompt": "Explain a SaaS business model.",
        "expect": {
            "topics_any": ["subscription", "recurring", "saas", "retention", "cac"],
            "prefer_providers_any": ["business_intelligence", "financial_concepts", "knowledge_factory"],
        },
    },
    # Moats (3)
    {
        "id": "GB20-MO01",
        "category": "Moats",
        "prompt": "What is HDFC Bank's moat?",
        "expect": {
            "must_mention": ["hdfc"],
            "topics_any": ["moat", "franchise", "deposit", "brand", "casa", "switching", "scale"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt"],
        },
    },
    {
        "id": "GB20-MO02",
        "category": "Moats",
        "prompt": "What is TCS's competitive advantage?",
        "expect": {
            "must_mention": ["tcs"],
            "topics_any": ["scale", "client", "delivery", "talent", "brand", "moat"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-MO03",
        "category": "Moats",
        "prompt": "Does Asian Paints have pricing power?",
        "expect": {
            "must_mention": ["asian paints"],
            "topics_any": ["pricing", "brand", "distribution", "moat", "power"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt"],
        },
    },
    # Competition (3)
    {
        "id": "GB20-CO01",
        "category": "Competition",
        "prompt": "Compare TCS vs Infosys.",
        "expect": {
            "must_mention": ["tcs", "infosys"],
            "comparison": True,
            "topics_any": ["scale", "margin", "growth", "services", "client"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-CO02",
        "category": "Competition",
        "prompt": "Compare DMart vs Reliance Retail.",
        "expect": {
            "must_mention": ["dmart", "reliance"],
            "comparison": True,
            "topics_any": ["retail", "store", "scale", "grocery", "format"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt"],
        },
    },
    {
        "id": "GB20-CO03",
        "category": "Competition",
        "prompt": "Compare Indigo vs Air India business models.",
        "expect": {
            "must_mention": ["indigo", "air india"],
            "comparison": True,
            "topics_any": ["airline", "lcc", "cost", "fleet", "aviation", "network"],
            "forbid": ["d & h india", "d and h india"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    # Unit Economics (2)
    {
        "id": "GB20-UE01",
        "category": "Unit Economics",
        "prompt": "Explain SaaS unit economics.",
        "expect": {
            "topics_any": ["cac", "ltv", "nrr", "subscription", "payback", "churn"],
            "prefer_providers_any": ["business_intelligence", "financial_concepts"],
        },
    },
    {
        "id": "GB20-UE02",
        "category": "Unit Economics",
        "prompt": "Explain airline economics.",
        "expect": {
            "topics_any": ["load factor", "fuel", "yield", "fleet", "cost", "cyclical"],
            "prefer_providers_any": ["business_intelligence", "financial_concepts", "knowledge_factory"],
        },
    },
    # Management (2)
    {
        "id": "GB20-MG01",
        "category": "Management",
        "prompt": "Evaluate management quality for Reliance Industries.",
        "expect": {
            "must_mention": ["reliance"],
            "topics_any": ["management", "capital allocation", "unknown", "governance", "evidence"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-MG02",
        "category": "Management",
        "prompt": "Compare Reliance and Adani as capital allocators.",
        "expect": {
            "must_mention": ["reliance", "adani"],
            "comparison": True,
            "topics_any": ["capital allocation", "capex", "debt", "roic", "leverage"],
        },
    },
    # Growth (2)
    {
        "id": "GB20-GR01",
        "category": "Growth",
        "prompt": "What drives growth for Infosys?",
        "expect": {
            "must_mention": ["infosys"],
            "topics_any": ["growth", "digital", "client", "volume", "pricing", "services"],
            "prefer_providers_any": ["business_intelligence", "capiq_ikt", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-GR02",
        "category": "Growth",
        "prompt": "Explain growth modes for a cement company.",
        "expect": {
            "topics_any": ["capacity", "volume", "pricing", "utilization", "growth"],
            "prefer_providers_any": ["business_intelligence", "knowledge_factory"],
        },
    },
    # Risks (2)
    {
        "id": "GB20-RK01",
        "category": "Risks",
        "prompt": "What are the biggest risks for a cement company?",
        "expect": {
            "topics_any": ["risk", "demand", "energy", "freight", "capacity", "cyclical"],
            "prefer_providers_any": ["business_intelligence", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-RK02",
        "category": "Risks",
        "prompt": "Why are airlines cyclical?",
        "expect": {
            "topics_any": ["cyclical", "demand", "fuel", "fixed cost", "capacity", "airline"],
            "prefer_providers_any": ["business_intelligence", "knowledge_factory"],
        },
    },
    # Industry Structure (2)
    {
        "id": "GB20-IN01",
        "category": "Industry Structure",
        "prompt": "Explain Porter's five forces for banks.",
        "expect": {
            "topics_any": ["porter", "rivalry", "barrier", "supplier", "customer", "bank"],
            "prefer_providers_any": ["business_intelligence", "knowledge_factory"],
        },
    },
    {
        "id": "GB20-IN02",
        "category": "Industry Structure",
        "prompt": "What are the key value drivers of an insurance company?",
        "expect": {
            "topics_any": ["premium", "underwriting", "float", "combined", "claims", "investment"],
            "prefer_providers_any": ["business_intelligence", "financial_concepts", "knowledge_factory"],
        },
    },
]

assert len(GOLDEN_BUSINESS_20) == 20


def _summary(payload: Dict[str, Any]) -> str:
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    return str(
        (ans.get("summary") if isinstance(ans, dict) else None)
        or payload.get("executive_summary")
        or payload.get("summary")
        or ""
    )


def _why(payload: Dict[str, Any]) -> List[str]:
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    why = (ans.get("why") if isinstance(ans, dict) else None) or payload.get("why") or []
    return [str(w) for w in why] if isinstance(why, list) else []


def _providers(payload: Dict[str, Any]) -> List[str]:
    orch = payload.get("ask_orchestration") or {}
    if not orch and isinstance(payload.get("degradation"), dict):
        orch = payload["degradation"].get("ask_orchestration") or {}
    orch = orch if isinstance(orch, dict) else {}
    providers = list(orch.get("kul_providers_used") or [])
    if not providers and isinstance(payload.get("coverage"), dict):
        providers = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    if not providers:
        providers = list(((payload.get("diagnostics") or {}).get("providers_used")) or [])
    return [str(p) for p in providers]


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip(), maxsplit=1)
    return parts[0] if parts else ""


_MENTION_ALIASES = {
    "tcs": ("tcs", "tata consultancy"),
    "infosys": ("infosys", "infy"),
    "hdfc": ("hdfc",),
    "reliance": ("reliance",),
    "dmart": ("dmart", "avenue supermarts"),
    "asian paints": ("asian paints", "asian paint"),
    "indigo": ("indigo", "indigo", "interglobe", "indiGo".lower()),
    "air india": ("air india", "airindia"),
    "adani": ("adani",),
    "jsw steel": ("jsw steel", "jswsteel", "jsw"),
}


def _mentions(phrase: str, low: str, why_join: str) -> bool:
    aliases = _MENTION_ALIASES.get(phrase.lower(), (phrase.lower(),))
    return any(a in low or a in why_join for a in aliases)


def evaluate_golden_business_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    expect = case.get("expect") or {}
    text = _summary(payload)
    why = _why(payload)
    low = text.lower()
    why_join = " ".join(why).lower()
    providers = _providers(payload)
    orch = payload.get("ask_orchestration") or {}
    if not orch and isinstance(payload.get("degradation"), dict):
        orch = payload["degradation"].get("ask_orchestration") or {}
    orch = orch if isinstance(orch, dict) else {}
    short_circuit = str(orch.get("short_circuit") or "")

    assertions: Dict[str, bool] = {}
    first = _first_sentence(text)
    assertions["direct_answer_first"] = bool(first) and not is_planning_scaffold(first) and len(first) >= 12
    assertions["no_framework_leakage"] = not (
        looks_like_framework_meta_executive(text)
        or is_planning_scaffold(text)
        or any(low.startswith(m) for m in HARD_FAIL_START_MARKERS)
    )
    assertions["has_summary"] = len(text.strip()) >= 24
    assertions["no_fabrication_flag"] = payload.get("fabricated") is not True

    for phrase in expect.get("must_mention") or []:
        assertions[f"mention:{phrase}"] = _mentions(phrase, low, why_join)

    topics = expect.get("topics_any") or []
    if topics:
        assertions["topic_substance"] = any(t.lower() in low or t.lower() in why_join for t in topics)

    if expect.get("comparison"):
        names = expect.get("must_mention") or []
        if len(names) >= 2:
            assertions["comparison_both"] = all(_mentions(n, low, why_join) for n in names)

    for phrase in expect.get("forbid") or []:
        assertions[f"forbid:{phrase}"] = phrase.lower() not in low and phrase.lower() not in why_join

    prefer = expect.get("prefer_providers_any") or []
    if prefer:
        assertions["institutional_path"] = any(p in providers for p in prefer) or short_circuit in {
            "knowledge_unification",
            "company_router",
            "ikt_company",
            "ikt_company_router",
        } or any(
            p in providers
            for p in ("institutional_knowledge_tables", "business_intelligence", "capiq_ikt")
        )
    soft_only = providers and all(p in {"legacy_kip", "academy"} for p in providers)
    assertions["no_generic_retrieval_only"] = not soft_only

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "pass": passed,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "providers": providers,
        "short_circuit": short_circuit,
        "summary": text[:240],
    }
