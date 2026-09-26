"""Industry Integration Acceptance Suite v1.0 — ~48 live questions via KUL.

Phase 3.1.5 gate: Industry Intelligence registered as first-class KUL provider,
industry questions routed to Industry DNA before generic retrieval, BI consumes
DNA rather than duplicating it.
"""

from __future__ import annotations

from typing import Any, Dict, List

II_INTEGRATION_CASES: List[Dict[str, Any]] = [
    # Industry Economics
    {
        "id": "III-EC01",
        "category": "industry_economics",
        "prompt": "Why are airlines low-margin businesses?",
        "require_ii": True,
        "must_any": ["airline", "margin", "load", "capital", "fuel", "cask", "rask"],
    },
    {
        "id": "III-EC02",
        "category": "industry_economics",
        "prompt": "Why do FMCG companies generate strong cash flow?",
        "require_ii": True,
        "must_any": ["fmcg", "cash", "brand", "working", "fcf", "capex"],
    },
    {
        "id": "III-EC03",
        "category": "industry_economics",
        "prompt": "Why do utilities use more debt?",
        "require_ii": True,
        "must_any": ["utilit", "debt", "leverage", "regulated", "cash", "rab"],
    },
    {
        "id": "III-EC04",
        "category": "industry_economics",
        "prompt": "Explain hospital industry economics.",
        "require_ii": True,
        "must_any": ["hospital", "occupancy", "arpob", "bed", "margin"],
    },
    {
        "id": "III-EC05",
        "category": "industry_economics",
        "prompt": "Explain cement industry economics.",
        "require_ii": True,
        "must_any": ["cement", "utilization", "realization", "cost", "cycle"],
    },
    {
        "id": "III-EC06",
        "category": "industry_economics",
        "prompt": "Why are chemical companies cyclical?",
        "require_ii": True,
        "must_any": ["chemical", "cycle", "spread", "feedstock", "commodity"],
    },
    {
        "id": "III-EC07",
        "category": "industry_economics",
        "prompt": "Why is working capital different in retail vs software?",
        "require_ii": True,
        "must_any": ["working", "retail", "software", "inventory", "cash", "deferred"],
    },
    {
        "id": "III-EC08",
        "category": "industry_economics",
        "prompt": "What drives profitability in diagnostics?",
        "require_ii": True,
        "must_any": ["diagnostic", "test", "volume", "realization", "lab", "margin"],
    },
    # KPIs
    {
        "id": "III-KP01",
        "category": "kpis",
        "prompt": "Explain NIM.",
        "require_ii": True,
        "must_any": ["nim", "interest", "margin", "spread", "nii"],
    },
    {
        "id": "III-KP02",
        "category": "kpis",
        "prompt": "Explain CASA.",
        "require_ii": True,
        "must_any": ["casa", "deposit", "funding", "current", "savings"],
    },
    {
        "id": "III-KP03",
        "category": "kpis",
        "prompt": "What is ARPOB?",
        "require_ii": True,
        "must_any": ["arpob", "bed", "revenue", "occupancy"],
    },
    {
        "id": "III-KP04",
        "category": "kpis",
        "prompt": "What is Load Factor?",
        "require_ii": True,
        "must_any": ["load", "factor", "seat", "passenger", "airline"],
    },
    {
        "id": "III-KP05",
        "category": "kpis",
        "prompt": "What is CET1 for banks?",
        "require_ii": True,
        "must_any": ["cet1", "capital", "rwa", "tier"],
    },
    {
        "id": "III-KP06",
        "category": "kpis",
        "prompt": "Explain SSSG in retail.",
        "require_ii": True,
        "must_any": ["same", "store", "sssg", "growth", "retail"],
    },
    {
        "id": "III-KP07",
        "category": "kpis",
        "prompt": "What is utilization in IT services?",
        "require_ii": True,
        "must_any": ["utilization", "billable", "bench", "it"],
    },
    {
        "id": "III-KP08",
        "category": "kpis",
        "prompt": "What is NRR for SaaS?",
        "require_ii": True,
        "must_any": ["nrr", "retention", "expansion", "churn", "saas", "software"],
    },
    # Valuation
    {
        "id": "III-VA01",
        "category": "valuation",
        "prompt": "Why are banks valued on P/B?",
        "require_ii": True,
        "must_any": ["p/b", "book", "equity", "roe", "bank"],
    },
    {
        "id": "III-VA02",
        "category": "valuation",
        "prompt": "Why is EV/Sales common for SaaS?",
        "require_ii": True,
        "must_any": ["ev/sales", "sales", "arr", "growth", "saas", "software"],
    },
    {
        "id": "III-VA03",
        "category": "valuation",
        "prompt": "Why is Embedded Value used for insurers?",
        "require_ii": True,
        "must_any": ["embedded", "vnb", "force", "insurance"],
    },
    {
        "id": "III-VA04",
        "category": "valuation",
        "prompt": "Why do telecoms use EV/EBITDA?",
        "require_ii": True,
        "must_any": ["ev/ebitda", "ebitda", "spectrum", "telecom"],
    },
    {
        "id": "III-VA05",
        "category": "valuation",
        "prompt": "Why is NAV used for real estate?",
        "require_ii": True,
        "must_any": ["nav", "propert", "asset", "real estate"],
    },
    {
        "id": "III-VA06",
        "category": "valuation",
        "prompt": "How are utilities typically valued?",
        "require_ii": True,
        "must_any": ["dcf", "yield", "rab", "regulated", "utilit"],
    },
    # Competition
    {
        "id": "III-CO01",
        "category": "competition",
        "prompt": "Why is the Indian telecom market an oligopoly?",
        "require_ii": True,
        "must_any": ["oligopol", "telecom", "spectrum", "barrier", "rivalry", "consol"],
    },
    {
        "id": "III-CO02",
        "category": "competition",
        "prompt": "Explain Porter's Five Forces for cement.",
        "require_ii": True,
        "must_any": ["cement", "rivalry", "barrier", "porter", "supplier", "entry"],
    },
    {
        "id": "III-CO03",
        "category": "competition",
        "prompt": "Describe competitive structure in banks.",
        "require_ii": True,
        "must_any": ["bank", "oligopol", "rivalry", "barrier", "entry"],
    },
    {
        "id": "III-CO04",
        "category": "competition",
        "prompt": "What is the competitive structure of Indian airlines?",
        "require_ii": True,
        "must_any": ["airline", "rivalry", "fragment", "oligopol", "barrier", "compet"],
    },
    # Regulation
    {
        "id": "III-RG01",
        "category": "regulation",
        "prompt": "Which regulator oversees banks in India?",
        "require_ii": True,
        "must_any": ["rbi"],
    },
    {
        "id": "III-RG02",
        "category": "regulation",
        "prompt": "Why does telecom depend on spectrum allocation?",
        "require_ii": True,
        "must_any": ["spectrum", "telecom", "trai", "dot", "license", "regulat"],
    },
    {
        "id": "III-RG03",
        "category": "regulation",
        "prompt": "Who regulates insurance in India?",
        "require_ii": True,
        "must_any": ["irdai"],
    },
    {
        "id": "III-RG04",
        "category": "regulation",
        "prompt": "Who regulates airlines in India?",
        "require_ii": True,
        "must_any": ["dgca"],
    },
    # Cross-industry / BI consumes DNA
    {
        "id": "III-XI01",
        "category": "cross_industry",
        "prompt": "Compare banks vs NBFCs.",
        "require_ii": True,
        "allow_bi": True,
        "must_any": ["bank", "nbfc", "funding", "deposit", "wholesale", "capital"],
    },
    {
        "id": "III-XI02",
        "category": "cross_industry",
        "prompt": "Why do SaaS companies scale differently from IT services?",
        "require_ii": True,
        "allow_bi": True,
        "must_any": ["saas", "software", "it", "margin", "utilization", "subscription", "nrr"],
    },
    {
        "id": "III-XI03",
        "category": "cross_industry",
        "prompt": "Compare airlines and railways.",
        "require_ii": True,
        "allow_bi": True,
        "must_any": ["airline", "capital", "load", "margin", "rail", "transport", "cycle"],
    },
    {
        "id": "III-XI04",
        "category": "cross_industry",
        "prompt": "Why do power utilities earn regulated returns?",
        "require_ii": True,
        "must_any": ["regulat", "return", "roe", "tariff", "rab", "utilit", "power"],
    },
    # Company + industry DNA fusion (BI leads, II consulted)
    {
        "id": "III-BI01",
        "category": "bi_consumes_dna",
        "prompt": "Compare TCS vs Infosys.",
        "require_ii": True,
        "require_bi": True,
        "must_any": ["tcs", "infosys", "it", "services", "utiliz", "margin", "digital"],
    },
    {
        "id": "III-BI02",
        "category": "bi_consumes_dna",
        "prompt": "Explain HDFC Bank's business model.",
        "require_ii": True,
        "require_bi": True,
        "must_any": ["hdfc", "bank", "deposit", "loan", "nim", "casa"],
    },
    {
        "id": "III-BI03",
        "category": "bi_consumes_dna",
        "prompt": "What is Infosys' business model?",
        "require_ii": True,
        "require_bi": True,
        "must_any": ["infosys", "it", "services", "digital", "client"],
    },
    # Cycles / risks
    {
        "id": "III-CY01",
        "category": "cycles",
        "prompt": "What cycle matters most for banks?",
        "require_ii": True,
        "must_any": ["credit", "cycle", "bank"],
    },
    {
        "id": "III-CY02",
        "category": "cycles",
        "prompt": "What cycle matters most for metals?",
        "require_ii": True,
        "must_any": ["commodity", "cycle", "metal"],
    },
    {
        "id": "III-RK01",
        "category": "industry_risks",
        "prompt": "What are the key risks in airlines?",
        "require_ii": True,
        "must_any": ["risk", "fuel", "demand", "airline", "capital"],
    },
    {
        "id": "III-RK02",
        "category": "industry_risks",
        "prompt": "What are the biggest risks for a cement company?",
        "require_ii": True,
        "allow_bi": True,
        "must_any": ["cement", "risk", "demand", "cost", "cycle", "commodity"],
    },
    # Cash / capital
    {
        "id": "III-CC01",
        "category": "cash_conversion",
        "prompt": "Explain cash conversion in FMCG.",
        "require_ii": True,
        "must_any": ["cash", "fmcg", "working", "brand"],
    },
    {
        "id": "III-CC02",
        "category": "cash_conversion",
        "prompt": "Explain cash conversion in software.",
        "require_ii": True,
        "must_any": ["cash", "software", "saas", "deferred", "fcf", "churn"],
    },
    {
        "id": "III-CA01",
        "category": "capital_allocation",
        "prompt": "What is typical capital allocation in banks?",
        "require_ii": True,
        "must_any": ["capital", "bank", "dividend", "cet1", "loan", "retain"],
    },
    {
        "id": "III-CA02",
        "category": "capital_allocation",
        "prompt": "What is typical capital allocation in utilities?",
        "require_ii": True,
        "must_any": ["capital", "utilit", "capex", "dividend", "debt", "rab"],
    },
    # Founder-sensitive industry set
    {
        "id": "III-FD01",
        "category": "founder",
        "prompt": "Why do banks use P/B?",
        "require_ii": True,
        "must_any": ["p/b", "book", "bank", "equity"],
    },
    {
        "id": "III-FD02",
        "category": "founder",
        "prompt": "Why do airlines earn low ROIC?",
        "require_ii": True,
        "must_any": ["airline", "roic", "capital", "fleet", "load"],
    },
    {
        "id": "III-FD03",
        "category": "founder",
        "prompt": "Why do hospitals have higher working capital?",
        "require_ii": True,
        "must_any": ["hospital", "working", "receivable", "payer", "insurer"],
    },
]

assert 40 <= len(II_INTEGRATION_CASES) <= 55, len(II_INTEGRATION_CASES)


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
        "analyse via",
    )
    if any(h in low for h in hedges):
        return False
    if low.startswith(("framework", "intent:", "planning:")):
        return False
    return True


def _blob(payload: Dict[str, Any]) -> str:
    parts = [payload.get("summary"), " ".join(payload.get("why") or [])]
    ci = payload.get("company_intelligence") or {}
    ind = ci.get("industry") if isinstance(ci, dict) else {}
    if isinstance(ind, dict):
        parts.append(str(ind))
    for r in payload.get("provider_results") or []:
        if isinstance(r, dict) and not r.get("empty"):
            parts.append(r.get("summary") or "")
            parts.append(" ".join(r.get("why") or []))
            raw = r.get("raw") or {}
            if isinstance(raw, dict):
                parts.append(str(raw.get("industry") or ""))
                parts.append(str(raw.get("industry_name") or ""))
                for key in ("economics", "valuation", "regulation", "competition", "kpis", "cross_industry"):
                    block = raw.get(key)
                    if isinstance(block, dict):
                        parts.append(block.get("summary") or "")
                    elif isinstance(block, list):
                        for item in block[:4]:
                            if isinstance(item, dict):
                                parts.append(item.get("name") or "")
                                parts.append(item.get("definition") or "")
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_ii_integration_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    diag = payload.get("diagnostics") or {}
    consulted = list(diag.get("providers_consulted") or [])
    plan_ids = list(((diag.get("plan") or {}).get("provider_ids")) or [])
    text = _blob(payload)
    summary = str(payload.get("summary") or "")

    assertions: Dict[str, bool] = {}

    if case.get("require_ii"):
        assertions["ii_selected"] = "industry_intelligence" in sources or (
            "industry_intelligence" in consulted
        )
        assertions["kul_plan_has_ii"] = (
            "industry_intelligence" in plan_ids or "industry_intelligence" in consulted
        )
        # Industry DNA used — provider consulted with industry fact, or summary grounded
        dna_used = (
            "industry_intelligence" in sources
            or "industry dna" in text
            or bool(((payload.get("company_intelligence") or {}).get("industry") or {}).get("from_industry_dna"))
            or any(m in text for m in (case.get("must_any") or [])[:2])
        )
        assertions["industry_dna_used"] = bool(dna_used)

    if case.get("require_bi"):
        assertions["bi_selected"] = "business_intelligence" in sources or (
            "business_intelligence" in consulted
        )

    assertions["no_generic_retrieval_only"] = sources != ["legacy_kip"] and (
        "legacy_kip" not in sources or len(sources) > 1
    )
    assertions["direct_answer_first"] = _summary_is_direct(summary)
    assertions["no_hallucination"] = payload.get("fabricated") is False
    assertions["no_framework_leakage"] = not summary.lower().startswith(
        ("analyse via", "framework", "intent:", "planning:")
    )

    must = case.get("must_any") or []
    if must:
        hits = sum(1 for m in must if m.lower() in text)
        need = 1 if len(must) <= 2 else min(2, len(must))
        assertions["topic_grounding"] = hits >= need

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "sources": sources,
        "consulted": consulted,
        "plan_ids": plan_ids,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": summary[:240],
        "pass": passed,
    }
