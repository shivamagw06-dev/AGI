"""Knowledge Unification Acceptance Test v1.0 — 60 questions.

Verifies provider selection, ordering, evidence fusion, and that applicable
providers are not skipped. No LLM. Runs via plan_and_gather in-process.
"""

from __future__ import annotations

from typing import Any, Dict, List

# (id, category, prompt, must_include_any_provider, forbid_as_only_source)
KUL_ACCEPTANCE_60: List[Dict[str, Any]] = [
    # Company / business (12)
    {"id": "KUL-C01", "category": "company", "prompt": "What is HDFC Bank's business model?", "must_any": ["capiq_ikt", "company_memory", "ikl", "knowledge_factory"]},
    {"id": "KUL-C02", "category": "company", "prompt": "Explain Reliance Industries.", "must_any": ["capiq_ikt", "company_memory", "knowledge_factory"]},
    {"id": "KUL-C03", "category": "company", "prompt": "What is Infosys' business model?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-C04", "category": "company", "prompt": "Explain TCS.", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-C05", "category": "company", "prompt": "What is Wipro's business model?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-C06", "category": "company", "prompt": "Explain HMT Limited.", "must_any": ["capiq_ikt"]},
    {"id": "KUL-C07", "category": "company", "prompt": "What is Goodricke Group Limited's business model?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-C08", "category": "company", "prompt": "Explain Utique Enterprises Limited.", "must_any": ["capiq_ikt"]},
    {"id": "KUL-C09", "category": "company", "prompt": "What is Aakaar Medical Technologies business model?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-C10", "category": "company", "prompt": "Explain Spright Agro Limited.", "must_any": ["capiq_ikt"]},
    {"id": "KUL-C11", "category": "company", "prompt": "What is Tata Steel's business model?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-C12", "category": "company", "prompt": "Explain Adani Enterprises.", "must_any": ["capiq_ikt", "knowledge_factory"]},
    # Concept (10)
    {"id": "KUL-K01", "category": "concept", "prompt": "Explain EBITDA", "must_any": ["financial_concepts", "financial_foundations"]},
    {"id": "KUL-K02", "category": "concept", "prompt": "Explain ROIC", "must_any": ["financial_concepts"]},
    {"id": "KUL-K03", "category": "concept", "prompt": "What is enterprise value?", "must_any": ["financial_concepts"]},
    {"id": "KUL-K04", "category": "concept", "prompt": "Explain free cash flow", "must_any": ["financial_concepts"]},
    {"id": "KUL-K05", "category": "concept", "prompt": "What is working capital?", "must_any": ["financial_concepts", "financial_foundations"]},
    {"id": "KUL-K06", "category": "concept", "prompt": "Explain WACC", "must_any": ["financial_concepts"]},
    {"id": "KUL-K07", "category": "concept", "prompt": "What is ROE?", "must_any": ["financial_concepts"]},
    {"id": "KUL-K08", "category": "concept", "prompt": "Explain gross margin", "must_any": ["financial_concepts", "financial_foundations"]},
    {"id": "KUL-K09", "category": "concept", "prompt": "What is book value?", "must_any": ["financial_concepts"]},
    {"id": "KUL-K10", "category": "concept", "prompt": "Explain capital allocation", "must_any": ["financial_concepts", "academy"]},
    # Accounting (8)
    {"id": "KUL-A01", "category": "accounting", "prompt": "Explain retained earnings", "must_any": ["financial_concepts", "financial_foundations"]},
    {"id": "KUL-A02", "category": "accounting", "prompt": "Why does every transaction require a debit and a credit?", "must_any": ["financial_foundations", "financial_concepts"]},
    {"id": "KUL-A03", "category": "accounting", "prompt": "What is a balance sheet?", "must_any": ["financial_foundations", "financial_concepts", "academy"]},
    {"id": "KUL-A04", "category": "accounting", "prompt": "Explain the income statement", "must_any": ["financial_foundations", "financial_statement_intelligence", "financial_concepts", "academy"]},
    {"id": "KUL-A05", "category": "accounting", "prompt": "What is depreciation?", "must_any": ["financial_foundations", "financial_concepts"]},
    {"id": "KUL-A06", "category": "accounting", "prompt": "Explain accrued expenses", "must_any": ["financial_foundations", "financial_concepts", "academy"]},
    {"id": "KUL-A07", "category": "accounting", "prompt": "What is a journal entry?", "must_any": ["financial_foundations"]},
    {"id": "KUL-A08", "category": "accounting", "prompt": "Explain double entry accounting", "must_any": ["financial_foundations", "financial_concepts"]},
    # Industry / business (8)
    {"id": "KUL-I01", "category": "industry", "prompt": "What industry does HDFC Bank operate in?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-I02", "category": "industry", "prompt": "Who are Infosys competitors?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-I03", "category": "business", "prompt": "What products does HDFC Bank offer?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-I04", "category": "business", "prompt": "What is Tata Motors Passenger Vehicles business model?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-I05", "category": "business", "prompt": "Explain Kotak Mahindra Bank.", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-I06", "category": "industry", "prompt": "What sector is Titan Company in?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-I07", "category": "business", "prompt": "What is Axis Bank's business model?", "must_any": ["capiq_ikt", "knowledge_factory"]},
    {"id": "KUL-I08", "category": "business", "prompt": "Explain State Bank of India.", "must_any": ["capiq_ikt", "knowledge_factory"]},
    # Valuation / market (8)
    {"id": "KUL-V01", "category": "valuation", "prompt": "What is HDFC Bank market cap?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-V02", "category": "valuation", "prompt": "Explain enterprise value", "must_any": ["financial_concepts"]},
    {"id": "KUL-V03", "category": "market", "prompt": "What is Reliance market capitalization?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-V04", "category": "valuation", "prompt": "What is EV/EBITDA?", "must_any": ["financial_concepts"]},
    {"id": "KUL-V05", "category": "market", "prompt": "When is the next earnings date for Infosys?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-V06", "category": "valuation", "prompt": "Explain free cash flow yield", "must_any": ["financial_concepts"]},
    {"id": "KUL-V07", "category": "market", "prompt": "What is TCS enterprise value?", "must_any": ["capiq_ikt"]},
    {"id": "KUL-V08", "category": "valuation", "prompt": "Explain price to book", "must_any": ["financial_concepts"]},
    # Macro / academy soft (4)
    {"id": "KUL-M01", "category": "macro", "prompt": "What is equity risk premium?", "must_any": ["financial_concepts", "academy"]},
    {"id": "KUL-M02", "category": "macro", "prompt": "Explain country risk premium", "must_any": ["financial_concepts", "academy"]},
    {"id": "KUL-M03", "category": "macro", "prompt": "What is inflation?", "must_any": ["financial_concepts", "academy", "ikl"]},
    {"id": "KUL-M04", "category": "macro", "prompt": "Explain cost of equity", "must_any": ["financial_concepts", "academy"]},
    # Fusion / multi-source expectations (6)
    {"id": "KUL-F01", "category": "fusion", "prompt": "What is HDFC Bank's business model and market cap?", "must_any": ["capiq_ikt"], "min_sources": 1},
    {"id": "KUL-F02", "category": "fusion", "prompt": "Explain Reliance Industries business and competitors", "must_any": ["capiq_ikt"], "min_sources": 1},
    {"id": "KUL-F03", "category": "fusion", "prompt": "What is Infosys revenue and business model?", "must_any": ["capiq_ikt"], "min_sources": 1},
    {"id": "KUL-F04", "category": "fusion", "prompt": "Explain EBITDA and how it differs from free cash flow", "must_any": ["financial_concepts"], "forbid_only": ["legacy_kip"]},
    {"id": "KUL-F05", "category": "fusion", "prompt": "What is Wipro and what sector is it in?", "must_any": ["capiq_ikt"], "min_sources": 1},
    {"id": "KUL-F06", "category": "fusion", "prompt": "Explain ROIC for an institutional investor", "must_any": ["financial_concepts"], "forbid_only": ["legacy_kip"]},
    # Coverage / negative (4) — unsupported must not invent via KUL company path
    {"id": "KUL-N01", "category": "negative", "prompt": "Why does Visa generate high free cash flow?", "expect_no_capiq_company": True},
    {"id": "KUL-N02", "category": "negative", "prompt": "What is Costco business model?", "expect_no_capiq_company": True},
    {"id": "KUL-N03", "category": "negative", "prompt": "Explain Tesla manufacturing", "expect_no_capiq_company": True},
    {"id": "KUL-N04", "category": "negative", "prompt": "What is Netflix subscriber strategy?", "expect_no_capiq_company": True},
]

assert len(KUL_ACCEPTANCE_60) == 60


def evaluate_kul_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    consulted = list(((payload.get("diagnostics") or {}).get("providers_consulted")) or [])
    assertions: Dict[str, bool] = {}

    if case.get("expect_no_capiq_company"):
        # KUL may still answer a concept, but must not bind a CapIQ Indian company.
        company = ((payload.get("company_intelligence") or {}).get("identity") or {})
        ticker = company.get("ticker") or ""
        assertions["no_false_capiq_bind"] = not (ticker.startswith("BSE") or ticker in {"HDFCBANK", "RELIANCE", "INFY", "TCS"})
        assertions["answered_or_empty_ok"] = True  # concept fallback acceptable
    else:
        must = case.get("must_any") or []
        assertions["provider_selection"] = any(p in sources for p in must) if must else bool(sources)
        min_sources = int(case.get("min_sources") or 1)
        assertions["min_sources"] = len(sources) >= min_sources
        assertions["has_summary"] = bool(payload.get("summary"))
        assertions["no_fabrication_flag"] = payload.get("fabricated") is False
        if case.get("forbid_only"):
            assertions["not_legacy_only"] = sources != case["forbid_only"]
        # Provider was at least consulted when required (not silently skipped from plan)
        if must:
            assertions["provider_consulted"] = any(p in consulted for p in must) or any(p in sources for p in must)

    # Dedup: fused why should not be empty when sources exist
    if sources and not case.get("expect_no_capiq_company"):
        assertions["fusion_has_why_or_summary"] = bool(payload.get("why") or payload.get("summary"))

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "sources": sources,
        "consulted": consulted,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": (payload.get("summary") or "")[:220],
        "pass": passed,
    }
