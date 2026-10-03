"""AGI Founder Evaluation V4 — investment-focused questions after INV→KUL wiring.

Gate: ≥95% pass.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ask_product_test.founder_evaluation_v2 import evaluate_founder_v2_case
from investment_intelligence.policy import has_recommendation_leak

FOUNDER_EVAL_V4_100: List[Dict[str, Any]] = []


def _add(section: str, prompt: str, topics: List[str], *, prefer_inv: bool = True):
    FOUNDER_EVAL_V4_100.append(
        {
            "id": f"FEV4-{len(FOUNDER_EVAL_V4_100)+1:03d}",
            "section": section,
            "prompt": prompt,
            "expect": {
                "topics_any": topics,
                "business_shaped": True,
                "prefer_inv_or_kul": prefer_inv,
            },
        }
    )


COMPANIES = [
    ("Reliance Industries", "reliance", ["reliance", "quality", "risk", "retail", "digital"]),
    ("TCS", "tcs", ["tcs", "quality", "margin", "deal", "utilization"]),
    ("Infosys", "infosys", ["infosys", "quality", "guidance", "deal", "margin"]),
    ("HDFC Bank", "hdfc", ["hdfc", "bank", "casa", "nim", "credit"]),
    ("Asian Paints", "asian", ["asian", "quality", "brand", "distribution", "margin"]),
    ("Berger Paints", "berger", ["berger", "quality", "share", "distribution"]),
    ("DMart", "dmart", ["dmart", "sssg", "store", "quality", "retail"]),
    ("JSW Steel", "jsw", ["jsw", "steel", "spread", "risk", "leverage"]),
    ("IndiGo", "indigo", ["indigo", "airline", "fuel", "load", "risk"]),
]

for name, key, topics in COMPANIES:
    _add("Investment Quality", f"Evaluate {name}'s investment quality.", topics + ["invest", "quality"])
    _add("Catalysts", f"What are {name}'s biggest catalysts?", topics[:3] + ["catalyst"])
    _add("Capital Allocation", f"Assess {name}'s capital allocation.", topics[:2] + ["capital", "allocat"])
    _add("Monitoring", f"Explain monitoring priorities for {name}.", topics[:3] + ["monitor"])
    _add("Risks", f"What are the major investment risks for {name}?", topics[:3] + ["risk"])
    _add("Evidence", f"Explain evidence strength for {name}.", topics[:2] + ["evidence", "strength"])
    _add("Scenarios", f"Outline bull, base, and bear scenarios for {name}.", topics[:2] + ["bull", "base", "bear"])
    _add("Thesis", f"What is the investment thesis for {name}?", topics[:3] + ["thesis", "invest"])

# Comparisons / founder classics
_add(
    "Comparisons",
    "Compare TCS and Infosys as businesses from an investment perspective.",
    ["tcs", "infosys", "quality", "invest"],
)
_add(
    "Comparisons",
    "Compare Asian Paints and Berger from a quality perspective.",
    ["asian", "berger", "quality"],
)
_add(
    "Founder",
    "Evaluate Reliance's investment quality.",
    ["reliance", "quality", "invest", "risk"],
)
_add(
    "Founder",
    "What are Infosys' biggest catalysts?",
    ["infosys", "catalyst"],
)
_add(
    "Founder",
    "Assess HDFC Bank's capital allocation.",
    ["hdfc", "capital", "allocat"],
)
_add(
    "Founder",
    "Explain monitoring priorities for Asian Paints.",
    ["asian", "monitor"],
)
_add(
    "Founder",
    "Evaluate JSW Steel's investment risks.",
    ["jsw", "risk", "steel"],
)
_add(
    "Founder",
    "Explain Berger Paints' evidence strength.",
    ["berger", "evidence", "strength"],
)
_add(
    "Founder",
    "Assess DMart's quality.",
    ["dmart", "quality"],
)
_add(
    "Founder",
    "Explain downside risks for IndiGo.",
    ["indigo", "risk", "fuel", "airline"],
)
_add(
    "Committee",
    "Run an investment committee simulation for Reliance Industries.",
    ["committee", "reliance", "recommend"],
)
_add(
    "Committee",
    "Run an investment committee simulation for TCS.",
    ["committee", "tcs"],
)

# Pad to exactly 100 with monitoring/risk variants
_pad = 0
while len(FOUNDER_EVAL_V4_100) < 100:
    name, key, topics = COMPANIES[_pad % len(COMPANIES)]
    _pad += 1
    _add(
        "Monitoring",
        f"How should investors monitor {name} (variant {_pad})?",
        topics[:3] + ["monitor"],
    )

del FOUNDER_EVAL_V4_100[100:]
for i, case in enumerate(FOUNDER_EVAL_V4_100, 1):
    case["id"] = f"FEV4-{i:03d}"

assert len(FOUNDER_EVAL_V4_100) == 100, len(FOUNDER_EVAL_V4_100)


def evaluate_founder_v4_case(
    case: Dict[str, Any],
    payload: Dict[str, Any],
    *,
    latency_ms: Optional[int] = None,
    http_status: Optional[int] = None,
    raw_html: bool = False,
) -> Dict[str, Any]:
    """V2 rubric + Investment Intelligence preference + no recommendation leakage."""
    expect = dict(case.get("expect") or {})
    case_v2 = dict(case)
    expect_v2 = dict(expect)
    if expect.get("prefer_inv_or_kul"):
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
    summary = str(
        ((payload.get("answer") or {}).get("summary"))
        or payload.get("executive_summary")
        or payload.get("summary")
        or ""
    )

    if expect.get("prefer_inv_or_kul") and not expect.get("policy_refuse"):
        inv_ok = (
            "investment_intelligence" in providers
            or "business_intelligence" in providers
            or "industry_intelligence" in providers
            or short_circuit == "knowledge_unification"
            or any(p in providers for p in ("capiq_ikt", "knowledge_factory"))
        )
        product["inv_or_institutional_path"] = bool(inv_ok)

    product["no_recommendation_leakage"] = not has_recommendation_leak(summary)

    product_ok = all(product.values()) if product else True
    hard = dict(base.get("hard_fail_flags") or {})
    score = int(base.get("final_score") or 0)
    if not product_ok and expect.get("business_shaped"):
        score = min(score, 17)
        hard["product_assertion_fail"] = True
    if has_recommendation_leak(summary):
        hard["recommendation_leakage"] = True
        score = min(score, 10)
    passed = score >= 18 and not hard and product_ok
    return {
        **base,
        "final_score": score,
        "hard_fail_flags": hard,
        "product_assertions": product,
        "pass": passed,
    }
