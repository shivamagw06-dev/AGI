"""AGI Founder Evaluation V3 — industry-focused questions after II→KUL wiring.

Reuses V2 product assertions and adds Industry DNA preferences.
Gate: ≥95% pass (same bar as V2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ask_product_test.founder_evaluation_v2 import evaluate_founder_v2_case

FOUNDER_EVAL_V3_20: List[Dict[str, Any]] = [
    {
        "id": "FEV3-01",
        "section": "Industry Economics",
        "prompt": "Explain hospital economics.",
        "expect": {
            "topics_any": ["hospital", "occupancy", "arpob", "bed", "margin", "payer"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-02",
        "section": "Industry Economics",
        "prompt": "Why are chemical companies cyclical?",
        "expect": {
            "topics_any": ["chemical", "cycle", "spread", "feedstock", "commodity"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-03",
        "section": "Cross Industry",
        "prompt": "Compare airlines and railways.",
        "expect": {
            "topics_any": ["airline", "rail", "capital", "load", "margin", "cycle"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-04",
        "section": "Working Capital",
        "prompt": "Why is working capital different in retail vs software?",
        "expect": {
            "topics_any": ["working", "retail", "software", "inventory", "cash", "deferred"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-05",
        "section": "Cross Industry",
        "prompt": "Compare banks vs NBFCs.",
        "expect": {
            "topics_any": ["bank", "nbfc", "deposit", "funding", "wholesale", "casa"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-06",
        "section": "Regulation",
        "prompt": "Why do power utilities earn regulated returns?",
        "expect": {
            "topics_any": ["regulat", "return", "tariff", "rab", "utilit", "power"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-07",
        "section": "Industry Economics",
        "prompt": "Explain cement industry economics.",
        "expect": {
            "topics_any": ["cement", "utilization", "realization", "cost", "cycle"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-08",
        "section": "Industry Economics",
        "prompt": "What drives profitability in diagnostics?",
        "expect": {
            "topics_any": ["diagnostic", "test", "volume", "realization", "lab", "margin"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-09",
        "section": "Cross Industry",
        "prompt": "Why do SaaS companies scale differently from IT services?",
        "expect": {
            "topics_any": ["saas", "software", "it", "margin", "utilization", "subscription", "nrr"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-10",
        "section": "Valuation",
        "prompt": "Why do banks use P/B?",
        "expect": {
            "topics_any": ["p/b", "book", "equity", "bank", "roe"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-11",
        "section": "KPIs",
        "prompt": "Explain NIM for banks.",
        "expect": {
            "topics_any": ["nim", "interest", "spread", "margin", "bank"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-12",
        "section": "KPIs",
        "prompt": "What is ARPOB?",
        "expect": {
            "topics_any": ["arpob", "bed", "revenue", "hospital", "occupancy"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-13",
        "section": "Valuation",
        "prompt": "Why is EV/Sales common for SaaS?",
        "expect": {
            "topics_any": ["ev/sales", "sales", "arr", "saas", "software", "growth"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-14",
        "section": "Competition",
        "prompt": "Why is the Indian telecom market an oligopoly?",
        "expect": {
            "topics_any": ["oligopol", "telecom", "spectrum", "barrier", "rivalry"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-15",
        "section": "Regulation",
        "prompt": "Which regulator oversees banks in India?",
        "expect": {
            "topics_any": ["rbi", "bank", "regulat"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-16",
        "section": "Industry Economics",
        "prompt": "Why are airlines low-margin businesses?",
        "expect": {
            "topics_any": ["airline", "margin", "load", "fuel", "capital", "cask"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-17",
        "section": "Cash",
        "prompt": "Why do FMCG companies generate strong cash flow?",
        "expect": {
            "topics_any": ["fmcg", "cash", "brand", "fcf", "working"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-18",
        "section": "Leverage",
        "prompt": "Why do utilities use more debt?",
        "expect": {
            "topics_any": ["utilit", "debt", "leverage", "regulated", "rab"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-19",
        "section": "Company + DNA",
        "prompt": "Compare TCS vs Infosys.",
        "expect": {
            "entities": ["tcs", "infosys"],
            "topics_any": ["it", "services", "utiliz", "margin", "digital", "client"],
            "business_shaped": True,
            "prefer_bi_or_kul": True,
            "prefer_ii_or_kul": True,
        },
    },
    {
        "id": "FEV3-20",
        "section": "Valuation",
        "prompt": "Why is Embedded Value used for insurers?",
        "expect": {
            "topics_any": ["embedded", "vnb", "insurance", "force"],
            "business_shaped": True,
            "prefer_ii_or_kul": True,
        },
    },
]

assert len(FOUNDER_EVAL_V3_20) == 20, len(FOUNDER_EVAL_V3_20)


def evaluate_founder_v3_case(
    case: Dict[str, Any],
    payload: Dict[str, Any],
    *,
    latency_ms: Optional[int] = None,
    http_status: Optional[int] = None,
    raw_html: bool = False,
) -> Dict[str, Any]:
    """V2 rubric + Industry Intelligence preference."""
    # Map prefer_ii_or_kul onto V2's prefer_bi_or_kul path for scoring, then tighten.
    expect = dict(case.get("expect") or {})
    case_v2 = dict(case)
    expect_v2 = dict(expect)
    if expect.get("prefer_ii_or_kul"):
        expect_v2["prefer_bi_or_kul"] = True
        expect_v2["business_shaped"] = True
    case_v2["expect"] = expect_v2

    base = evaluate_founder_v2_case(
        case_v2,
        payload,
        latency_ms=latency_ms,
        http_status=http_status,
        raw_html=raw_html,
    )
    product = dict(base.get("product_assertions") or {})
    providers = list(base.get("providers") or [])
    short_circuit = str(base.get("short_circuit") or "")

    if expect.get("prefer_ii_or_kul") and not expect.get("policy_refuse"):
        ii_ok = (
            "industry_intelligence" in providers
            or "business_intelligence" in providers
            or short_circuit == "knowledge_unification"
            or any(
                p in providers
                for p in (
                    "capiq_ikt",
                    "financial_concepts",
                    "knowledge_factory",
                )
            )
        )
        product["ii_or_institutional_path"] = bool(ii_ok)

    product_ok = all(product.values()) if product else True
    hard = dict(base.get("hard_fail_flags") or {})
    score = int(base.get("final_score") or 0)
    if not product_ok and expect.get("business_shaped"):
        score = min(score, 17)
        hard["product_assertion_fail"] = True
    passed = score >= 18 and not hard and product_ok
    return {
        **base,
        "final_score": score,
        "hard_fail_flags": hard,
        "product_assertions": product,
        "pass": passed,
    }
