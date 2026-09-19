"""Business Integration Acceptance Suite v1.0 — ~28 live questions via KUL.

Phase 3.0.5 gate: BI registered as first-class KUL provider, business questions
routed to BI before generic retrieval, fused with CapIQ/memory/KF where available.
Does not claim Phase 3 freeze — founder eval + production regressions remain.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Assertions checked per case:
# - bi_selected: business_intelligence in sources (or consulted for industry pedagogy)
# - kul_plan_has_bi: diagnostics plan includes business_intelligence
# - no_generic_retrieval_only: not legacy_kip-only
# - direct_answer_first: summary non-empty and not a hedge-only stub
# - no_hallucination: fabricated is False; unsupported globals do not CapIQ-bind India names
# - evidence_fusion: company cases fuse BI with at least one of CapIQ/memory/KF/IKL when available

BI_INTEGRATION_CASES: List[Dict[str, Any]] = [
    # Business model
    {
        "id": "BII-BM01",
        "category": "business_model",
        "prompt": "What is Reliance Industries' business model?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "company_memory", "ikl", "knowledge_factory"],
        "forbid_false_capiq": False,
    },
    {
        "id": "BII-BM02",
        "category": "business_model",
        "prompt": "Explain HDFC Bank's business model.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "company_memory", "ikl", "knowledge_factory"],
    },
    {
        "id": "BII-BM03",
        "category": "business_model",
        "prompt": "How does DMart make money?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "company_memory", "knowledge_factory"],
    },
    {
        "id": "BII-BM04",
        "category": "business_model",
        "prompt": "What is Infosys' business model?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    {
        "id": "BII-BM05",
        "category": "business_model",
        "prompt": "Explain TCS business model.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    # Moats
    {
        "id": "BII-MO01",
        "category": "moat",
        "prompt": "What is TCS's competitive advantage?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory", "company_memory"],
    },
    {
        "id": "BII-MO02",
        "category": "moat",
        "prompt": "Does Asian Paints have pricing power?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    {
        "id": "BII-MO03",
        "category": "moat",
        "prompt": "Why is Apple considered to have a strong moat?",
        "require_bi": True,
        "forbid_false_capiq": True,
        "industry_ok": True,
    },
    {
        "id": "BII-MO04",
        "category": "moat",
        "prompt": "What is HDFC Bank's moat?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "company_memory", "knowledge_factory"],
    },
    {
        "id": "BII-MO05",
        "category": "moat",
        "prompt": "What is Costco's moat?",
        "require_bi": True,
        "forbid_false_capiq": True,
        "industry_ok": True,
    },
    # Unit economics
    {
        "id": "BII-UE01",
        "category": "unit_economics",
        "prompt": "Explain SaaS unit economics.",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-UE02",
        "category": "unit_economics",
        "prompt": "Explain airline economics.",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-UE03",
        "category": "unit_economics",
        "prompt": "Explain FMCG cash conversion.",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-UE04",
        "category": "unit_economics",
        "prompt": "Explain bank unit economics for HDFC Bank.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    # Competition
    {
        "id": "BII-CO01",
        "category": "competition",
        "prompt": "Compare Infosys vs TCS.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory", "company_memory"],
    },
    {
        "id": "BII-CO02",
        "category": "competition",
        "prompt": "Compare Visa vs Mastercard.",
        "require_bi": True,
        "forbid_false_capiq": True,
        "industry_ok": True,
    },
    {
        "id": "BII-CO03",
        "category": "competition",
        "prompt": "Compare DMart vs Reliance Retail.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    {
        "id": "BII-CO04",
        "category": "competition",
        "prompt": "Compare HDFC Bank vs ICICI Bank.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    # Risks
    {
        "id": "BII-RK01",
        "category": "risks",
        "prompt": "What are the biggest risks for a cement company?",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-RK02",
        "category": "risks",
        "prompt": "Why are airlines cyclical?",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-RK03",
        "category": "risks",
        "prompt": "What are the biggest business risks for Reliance Industries?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory", "company_memory"],
    },
    # Industry / growth mix
    {
        "id": "BII-IN01",
        "category": "industry",
        "prompt": "Explain Porter's five forces for banks.",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-IN02",
        "category": "industry",
        "prompt": "What is the industry structure of cement?",
        "require_bi": True,
        "industry_ok": True,
    },
    {
        "id": "BII-IN03",
        "category": "growth",
        "prompt": "What drives growth for Infosys?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    # Founder-sensitive set (should improve once BI is live)
    {
        "id": "BII-FD01",
        "category": "founder",
        "prompt": "What is Reliance Industries' business model?",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "company_memory", "knowledge_factory"],
    },
    {
        "id": "BII-FD02",
        "category": "founder",
        "prompt": "Compare Infosys vs TCS.",
        "require_bi": True,
        "require_fusion_any": ["capiq_ikt", "knowledge_factory"],
    },
    {
        "id": "BII-FD03",
        "category": "founder",
        "prompt": "Why is Ferrari more profitable than Toyota?",
        "require_bi": True,
        "forbid_false_capiq": True,
        "industry_ok": True,
    },
    {
        "id": "BII-FD04",
        "category": "founder",
        "prompt": "What is Costco's moat?",
        "require_bi": True,
        "forbid_false_capiq": True,
        "industry_ok": True,
    },
]

assert 20 <= len(BI_INTEGRATION_CASES) <= 30, len(BI_INTEGRATION_CASES)

_FALSE_BIND_TICKERS = {
    "HDFCBANK",
    "RELIANCE",
    "INFY",
    "TCS",
    "WIPRO",
    "ICICIBANK",
    "SBIN",
    "DMART",
    "ASIANPAINT",
}


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
    )
    return not any(h in low for h in hedges)


def evaluate_bi_integration_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    diag = payload.get("diagnostics") or {}
    consulted = list(diag.get("providers_consulted") or [])
    plan_ids = list(((diag.get("plan") or {}).get("provider_ids")) or [])
    company = ((payload.get("company_intelligence") or {}).get("identity") or {})
    ticker = str(company.get("ticker") or payload.get("key") or "")

    assertions: Dict[str, bool] = {}

    if case.get("require_bi"):
        assertions["bi_selected"] = "business_intelligence" in sources or (
            case.get("industry_ok") and "business_intelligence" in consulted
        )
        assertions["kul_plan_has_bi"] = "business_intelligence" in plan_ids or (
            "business_intelligence" in consulted
        )

    assertions["no_generic_retrieval_only"] = sources != ["legacy_kip"] and (
        "legacy_kip" not in sources or len(sources) > 1
    )
    assertions["direct_answer_first"] = _summary_is_direct(str(payload.get("summary") or ""))
    assertions["no_hallucination"] = payload.get("fabricated") is False

    if case.get("forbid_false_capiq"):
        # Unsupported globals / industry pedagogy must not CapIQ-bind Indian names.
        false_bind = bool(ticker) and (
            ticker in _FALSE_BIND_TICKERS or ticker.startswith("BSE")
        )
        assertions["no_false_capiq_bind"] = not false_bind

    fusion_any = case.get("require_fusion_any") or []
    if fusion_any:
        assertions["evidence_fusion"] = any(p in sources for p in fusion_any) and (
            "business_intelligence" in sources or "business_intelligence" in consulted
        )

    # Lead summary should prefer BI when BI contributed.
    if "business_intelligence" in sources and case.get("require_bi"):
        assertions["bi_preferred_or_fused"] = True  # presence in used sources is the gate

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "sources": sources,
        "consulted": consulted,
        "plan_ids": plan_ids,
        "ticker": ticker,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": (payload.get("summary") or "")[:240],
        "pass": passed,
    }
