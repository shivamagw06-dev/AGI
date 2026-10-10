"""AGI Answer Quality Acceptance v1.0 — 500 questions (Phase 4.0).

Core Platform Acceptance proves AGI answers *safely*: right route, right
entity, no hallucination, no recommendation leakage. It does not prove AGI
answers *well*.

This suite measures institutional depth, company specificity, evidence
quality, research depth and executive communication — and fails answers that
are technically correct but generic.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUITE_VERSION = "1.0.0"
SECTION_SIZE = 50
OVERALL_TARGET_PCT = 95.0
CASE_PASS_SCORE = 70.0
BOILERPLATE_SIMILARITY = 0.85

# Weighted quality dimensions (spec weights).
DIMENSION_WEIGHTS: dict[str, int] = {
    "answers_question": 20,
    "company_specificity": 15,
    "industry_specificity": 10,
    "evidence_quality": 15,
    "financial_reasoning": 15,
    "executive_communication": 10,
    "research_depth": 10,
    "boilerplate_penalty": 5,
    "honest_uncertainty": 5,
}

# Which dimensions apply to which section.
SECTION_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "A_company": ("answers_question", "company_specificity", "industry_specificity",
                  "evidence_quality", "executive_communication", "boilerplate_penalty"),
    "B_financial": ("answers_question", "financial_reasoning", "executive_communication",
                    "boilerplate_penalty"),
    "C_business": ("answers_question", "company_specificity", "industry_specificity",
                   "evidence_quality", "executive_communication", "boilerplate_penalty"),
    "D_industry": ("answers_question", "industry_specificity", "financial_reasoning",
                   "executive_communication", "boilerplate_penalty"),
    "E_investment": ("answers_question", "company_specificity", "evidence_quality",
                     "financial_reasoning", "executive_communication", "boilerplate_penalty"),
    "F_research": ("answers_question", "company_specificity", "research_depth",
                   "evidence_quality", "executive_communication", "boilerplate_penalty"),
    "G_consensus": ("answers_question", "company_specificity", "evidence_quality",
                    "executive_communication", "boilerplate_penalty"),
    "H_fusion": ("answers_question", "company_specificity", "industry_specificity",
                 "evidence_quality", "executive_communication", "boilerplate_penalty"),
    "I_executive": ("answers_question", "executive_communication", "boilerplate_penalty"),
    "J_impossible": ("answers_question", "honest_uncertainty", "executive_communication"),
}

GOLDEN: tuple[tuple[str, str], ...] = (
    ("AXISBANK", "Axis Bank"),
    ("HDFCBANK", "HDFC Bank"),
    ("ICICIBANK", "ICICI Bank"),
    ("SBIN", "State Bank of India"),
    ("INFY", "Infosys"),
    ("TCS", "Tata Consultancy Services"),
    ("HCLTECH", "HCL Technologies"),
    ("WIPRO", "Wipro"),
    ("RELIANCE", "Reliance Industries"),
    ("ONGC", "Oil and Natural Gas Corporation"),
    ("BPCL", "Bharat Petroleum Corporation"),
    ("IOC", "Indian Oil Corporation"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("JSWSTEEL", "JSW Steel"),
    ("TATASTEEL", "Tata Steel"),
    ("ASIANPAINT", "Asian Paints"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries"),
    ("APOLLOHOSP", "Apollo Hospitals"),
    ("TITAN", "Titan Company"),
    ("DMART", "Avenue Supermarts"),
    ("TRENT", "Trent"),
    ("ITC", "ITC"),
    ("NESTLEIND", "Nestle India"),
    ("LT", "Larsen & Toubro"),
    ("NTPC", "NTPC"),
    ("POWERGRID", "Power Grid Corporation of India"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("DLF", "DLF"),
    ("MARUTI", "Maruti Suzuki India"),
    ("INDIGO", "InterGlobe Aviation"),
)

_A_TEMPLATES = ("Explain {name}", "What does {name} do?")
_C_TEMPLATES = (
    "What is {name}'s business model?",
    "What is {name}'s moat?",
    "Who competes with {name}?",
    "Explain the unit economics of {name}",
    "What drives growth at {name}?",
)
_E_TEMPLATES = (
    "What is the investment thesis for {name}?",
    "What are the biggest risks for {name}?",
    "Why would an investor own {name}?",
    "What are the key catalysts for {name}?",
    "Assess business and financial quality at {name}",
)
_F_TEMPLATES = (
    "What did {name}'s annual report say?",
    "What has management said at {name}?",
    "How does {name} allocate capital?",
    "What guidance has {name} given?",
    "Summarise {name}'s latest earnings call",
)
_G_TEMPLATES = (
    "What is the consensus target price for {name}?",
    "What is the high target for {name}?",
    "What is the low target for {name}?",
    "How many analysts cover {name}?",
    "What is the analyst rating split for {name}?",
)
_H_TEMPLATES = (
    "Give me a full institutional view on {name}",
    "Explain {name}'s business, industry position and what the street thinks",
)
_I_TEMPLATES = (
    "In one paragraph, what should I know about {name}?",
    "Brief me on {name} like an analyst would",
)

_B_QUESTIONS = (
    "Why can PAT rise while operating cash flow falls?",
    "Why can a profitable company run out of cash?",
    "How do receivables affect cash flow?",
    "How does inventory build-up hide weak demand?",
    "Why do payables flatter operating cash flow?",
    "Explain the difference between EBITDA and operating cash flow",
    "Why is depreciation added back to cash flow?",
    "How does working capital consume growth capital?",
    "Explain the cash conversion cycle and why it matters",
    "Why can revenue growth destroy value?",
    "How do you reconcile PAT to free cash flow?",
    "Why does ROIC matter more than growth?",
    "Explain incremental ROIC",
    "Why is book value the wrong lens for asset-light firms?",
    "How does operating leverage amplify earnings?",
    "Why can margins expand while returns fall?",
    "Explain the DuPont decomposition of ROE",
    "How does leverage flatter ROE?",
    "Why do provisions distort reported profit?",
    "Explain deferred tax and why it matters",
    "How does revenue recognition affect earnings quality?",
    "Why can EBITDA overstate economic profit?",
    "Explain the difference between accrual and cash profit",
    "How do you spot earnings quality problems?",
    "Why does capex timing distort free cash flow?",
)

_D_QUESTIONS = (
    "How are banks valued?",
    "What KPIs matter for banks?",
    "Explain bank unit economics",
    "What drives value for banks?",
    "What KPIs matter for telecom?",
    "How is telecom valued?",
    "Explain airline economics",
    "What KPIs matter for airlines?",
    "How are airlines valued?",
    "What drives value in cement?",
    "What KPIs matter for cement?",
    "How is cement valued?",
    "What KPIs matter for hospitals?",
    "How are hospitals valued?",
    "Explain hospital unit economics",
    "How is IT services valued?",
    "What KPIs matter for IT services?",
    "Explain IT services unit economics",
    "How are FMCG companies valued?",
    "What KPIs matter for FMCG?",
    "How are refiners valued?",
    "What KPIs matter for refiners?",
    "How is retail valued?",
    "What KPIs matter for retail?",
    "How are utilities valued?",
)

_J_QUESTIONS = (
    "PAT doubled. Why?",
    "Revenue increased. Why?",
    "Cash fell. Why?",
    "Explain XYZ Robotics Pvt Ltd",
    "What is Quorvex Analytics Private Limited's business model?",
    "Explain Zentara Quantum Systems Limited",
    "Should I buy HDFC Bank tomorrow?",
    "Should I sell Infosys this week?",
    "Give me a target price for Reliance Industries",
    "What will the Nifty close at tomorrow?",
    "Explain Apollo",
    "Explain Birla",
    "What is HDFC?",
    "What sector is Tata in?",
    "Which stock will double next month?",
)


def _fill(templates: tuple[str, ...], count: int, section: str, prefix: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for template in templates:
        for ticker, name in GOLDEN:
            if len(cases) >= count:
                return cases
            cases.append(
                {
                    "id": f"{prefix}-{len(cases) + 1:03d}",
                    "section": section,
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "company": name,
                }
            )
    return cases


def _repeat(questions: tuple[str, ...], count: int, section: str, prefix: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for i in range(count):
        cases.append(
            {
                "id": f"{prefix}-{i + 1:03d}",
                "section": section,
                "question": questions[i % len(questions)],
            }
        )
    return cases


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    cases += _fill(_A_TEMPLATES, SECTION_SIZE, "A_company", "AQ-A")
    cases += _repeat(_B_QUESTIONS, SECTION_SIZE, "B_financial", "AQ-B")
    cases += _fill(_C_TEMPLATES, SECTION_SIZE, "C_business", "AQ-C")
    cases += _repeat(_D_QUESTIONS, SECTION_SIZE, "D_industry", "AQ-D")
    cases += _fill(_E_TEMPLATES, SECTION_SIZE, "E_investment", "AQ-E")
    cases += _fill(_F_TEMPLATES, SECTION_SIZE, "F_research", "AQ-F")
    cases += _fill(_G_TEMPLATES, SECTION_SIZE, "G_consensus", "AQ-G")
    cases += _fill(_H_TEMPLATES, SECTION_SIZE, "H_fusion", "AQ-H")
    cases += _fill(_I_TEMPLATES, SECTION_SIZE, "I_executive", "AQ-I")
    cases += _repeat(_J_QUESTIONS, SECTION_SIZE, "J_impossible", "AQ-J")
    return cases


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
_ENTITY_REFUSAL_RE = re.compile(
    r"could not verify a canonical institutional entity|"
    r"do not currently have verified institutional coverage|"
    r"no verified entity",
    re.I,
)
_UNCERTAINTY_RE = re.compile(
    r"(\bcannot\b|can't|could not|not able to|no coverage|not covered|insufficient|"
    r"unable to|do(?:es)?\s+not\s+(?:\w+\s+){0,2}(?:issue|provide|have|know)|"
    r"\bno\s+verified\b|not\s+verif\w+|unverified|will not (?:guess|substitute)|"
    r"which one do you mean|clarif\w+|monitoring only|uncertain|"
    r"more (?:context|information) (?:is )?(?:needed|required))",
    re.I,
)
_SCAFFOLDING_RE = re.compile(
    r"\b(sources fused|providers? used|knowledge_unification|capiq_ikt|business_intelligence|"
    r"industry_intelligence|investment_intelligence|research_intelligence|valuation_consensus|"
    r"company_memory|legacy_kip|financial_foundations|financial_concepts|"
    r"knowledge factory|planner|provider_id|short_circuit)\b",
    re.I,
)
_AGI_RECOMMENDATION_RE = re.compile(
    r"\b(we recommend (?:buying|selling)|you should (?:buy|sell)|"
    r"our (?:rating|recommendation) is|rating\s*[:=]\s*(?:buy|sell))\b",
    re.I,
)
_GENERIC_DRIVER_RE = re.compile(
    r"^\s*for [a-z_ ]+, enterprise value is primarily driven by", re.I
)
_CONSENSUS_LABEL_RE = re.compile(
    r"(capital iq|market consensus|consensus target|analysts? cover|broker)", re.I
)
_RESEARCH_EVIDENCE_RE = re.compile(
    r"\b(annual report|earnings call|transcript|guidance|management (?:said|commentary|discussion)|"
    r"md&a|filing|investor presentation|capital allocation|fy20\d\d|quarterly results)\b",
    re.I,
)
_THESIS_EVIDENCE_RE = re.compile(
    r"\b(thesis|business quality|financial quality|industry position|risk|catalyst|"
    r"valuation|evidence|monitor|scenario|bull|bear|moat|franchise)\b",
    re.I,
)
_FINANCIAL_REASONING_RE = re.compile(
    r"\b(because|therefore|so that|which means|as a result|driven by|leads to|"
    r"while|whereas|even though|however|the reason)\b",
    re.I,
)
_NUMBER_RE = re.compile(r"\b\d[\d,.]*\b")


def _normalise(text: str) -> str:
    # Fold accents so "Nestlé India" matches the "Nestle India" prompt.
    folded = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", folded.lower())


def _tokens(text: str) -> list[str]:
    return [t for t in _normalise(text).split() if t]


def _company_tokens(name: str) -> list[str]:
    stop = {"limited", "ltd", "the", "of", "and", "india", "indian", "corporation", "company"}
    return [t for t in _tokens(name) if t not in stop and len(t) > 2]


def _score_case(
    case: dict[str, Any],
    text: str,
    payload: dict[str, Any],
    identity: Any,
) -> tuple[dict[str, float], list[str]]:
    """Return (dimension scores 0..1, automatic-fail reasons)."""
    section = case["section"]
    low = (text or "").lower()
    words = _tokens(text)
    fails: list[str] = []
    dims: dict[str, float] = {}

    refused = bool(_ENTITY_REFUSAL_RE.search(text or ""))
    generic_driver = bool(_GENERIC_DRIVER_RE.search((text or "").strip()))

    # ---- automatic fails -------------------------------------------------
    if _AGI_RECOMMENDATION_RE.search(text or ""):
        fails.append("recommendation_leakage")
    if section == "D_industry" and refused:
        fails.append("industry_refusal")
    if section != "J_impossible" and refused:
        fails.append("unexpected_refusal")
    if section == "E_investment" and generic_driver:
        fails.append("investment_without_thesis")
    if section == "F_research" and not _RESEARCH_EVIDENCE_RE.search(text or ""):
        fails.append("research_without_research")
    if section in {"A_company", "C_business", "H_fusion", "I_executive"} and case.get("company"):
        low = _normalise(text)
        hits = sum(1 for t in _company_tokens(case["company"]) if t in low)
        if hits == 0 and not refused:
            fails.append("company_without_company")
    if section == "G_consensus" and not _CONSENSUS_LABEL_RE.search(text or ""):
        fails.append("consensus_without_label")

    # ---- dimensions ------------------------------------------------------
    applicable = SECTION_DIMENSIONS[section]

    if "answers_question" in applicable:
        if not words:
            dims["answers_question"] = 0.0
        elif section == "J_impossible":
            dims["answers_question"] = 1.0 if _UNCERTAINTY_RE.search(text or "") else 0.0
        elif refused or generic_driver:
            dims["answers_question"] = 0.0
        else:
            dims["answers_question"] = 1.0 if len(words) >= 25 else 0.4

    if "company_specificity" in applicable:
        company = case.get("company") or ""
        toks = _company_tokens(company)
        hits = sum(1 for t in toks if t in low)
        named = hits / max(1, len(toks))
        # A company answer should also carry facts, not only the name.
        detail = 1.0 if _NUMBER_RE.search(text or "") or len(words) >= 60 else 0.5
        dims["company_specificity"] = 0.0 if generic_driver else min(1.0, named * detail)

    if "industry_specificity" in applicable:
        vocab = ("nim", "casa", "gnpa", "arpu", "arpob", "sssg", "utilization", "attrition",
                 "load factor", "grm", "realization", "occupancy", "capacity", "spread",
                 "credit cost", "premium", "tonne", "footfall", "churn", "yield", "pricing",
                 "cycle", "regulat", "margin", "volume")
        hits = sum(1 for v in vocab if v in low)
        dims["industry_specificity"] = min(1.0, hits / 3.0)

    if "evidence_quality" in applicable:
        evidence = payload.get("evidence_used") if isinstance(payload, dict) else []
        n_ev = len(evidence) if isinstance(evidence, list) else 0
        has_signal = bool(_NUMBER_RE.search(text or "")) or n_ev > 0
        dims["evidence_quality"] = 0.0 if (refused or generic_driver) else (1.0 if has_signal else 0.4)

    if "financial_reasoning" in applicable:
        causal = len(_FINANCIAL_REASONING_RE.findall(text or ""))
        if section == "B_financial":
            dims["financial_reasoning"] = min(1.0, causal / 2.0) if len(words) >= 30 else 0.2
        else:
            dims["financial_reasoning"] = min(1.0, causal / 2.0)

    if "executive_communication" in applicable:
        score = 1.0
        if _SCAFFOLDING_RE.search(text or ""):
            score -= 0.6
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s]
        if sentences:
            first = sentences[0]
            if len(_tokens(first)) > 45:
                score -= 0.2
        # repeated sentences read as filler
        if sentences and len(sentences) != len({s.strip().lower() for s in sentences}):
            score -= 0.3
        dims["executive_communication"] = max(0.0, score)

    if "research_depth" in applicable:
        hits = len(set(_RESEARCH_EVIDENCE_RE.findall(text or "")))
        dims["research_depth"] = min(1.0, hits / 2.0)

    if "boilerplate_penalty" in applicable:
        dims["boilerplate_penalty"] = 0.0 if generic_driver else 1.0

    if "honest_uncertainty" in applicable:
        dims["honest_uncertainty"] = 1.0 if _UNCERTAINTY_RE.search(text or "") else 0.0

    return dims, fails


def _weighted(dims: dict[str, float]) -> float:
    total_w = sum(DIMENSION_WEIGHTS[d] for d in dims)
    if not total_w:
        return 0.0
    return round(sum(DIMENSION_WEIGHTS[d] * v for d, v in dims.items()) / total_w * 100.0, 2)


def detect_boilerplate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag near-identical answers to different companies in the same section."""
    clusters: list[dict[str, Any]] = []
    by_section: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        if r.get("company"):
            by_section.setdefault(r["section"], []).append(r)

    for section, rows in by_section.items():
        # Group by template so only comparable prompts are compared.
        by_template: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            template = re.sub(re.escape(r["company"]), "{name}", r["question"], flags=re.I)
            by_template.setdefault(template, []).append(r)
        for template, group in by_template.items():
            seen: list[dict[str, Any]] = []
            for r in group:
                body = _normalise(r["answer"])
                match = None
                for other in seen:
                    ratio = SequenceMatcher(None, body, _normalise(other["answer"])).ratio()
                    if ratio >= BOILERPLATE_SIMILARITY:
                        match = (other, round(ratio, 3))
                        break
                if match:
                    r["boilerplate_with"] = match[0]["id"]
                    r["boilerplate_similarity"] = match[1]
                    clusters.append(
                        {
                            "section": section,
                            "template": template,
                            "id": r["id"],
                            "matches": match[0]["id"],
                            "similarity": match[1],
                            "companies": [r["company"], match[0]["company"]],
                            "answer": r["answer"][:180],
                        }
                    )
                else:
                    seen.append(r)
    return clusters


def summarise(results: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    overall = round((passed / total) * 100.0, 2) if total else 0.0

    sections: dict[str, dict[str, Any]] = {}
    for r in results:
        b = sections.setdefault(r["section"], {"total": 0, "passed": 0, "score_sum": 0.0})
        b["total"] += 1
        b["passed"] += 1 if r["passed"] else 0
        b["score_sum"] += r["score"]
    for b in sections.values():
        b["pass_rate_pct"] = round((b["passed"] / b["total"]) * 100.0, 2) if b["total"] else 0.0
        b["avg_score"] = round(b["score_sum"] / b["total"], 2) if b["total"] else 0.0
        b.pop("score_sum", None)

    def _fail_count(reason: str) -> int:
        return sum(1 for r in results if reason in r["fails"])

    weak_companies = sorted(
        (
            {
                "company": company,
                "avg_score": round(sum(x["score"] for x in rows) / len(rows), 2),
                "failures": sum(1 for x in rows if not x["passed"]),
            }
            for company, rows in _group(results, "company").items()
        ),
        key=lambda x: x["avg_score"],
    )[:12]

    weak_questions = sorted(results, key=lambda r: r["score"])[:50]

    dimension_avg: dict[str, float] = {}
    for dim in DIMENSION_WEIGHTS:
        vals = [r["dimensions"][dim] for r in results if dim in r["dimensions"]]
        if vals:
            dimension_avg[dim] = round(sum(vals) / len(vals) * 100.0, 2)

    gates = {
        "boilerplate": len(clusters),
        "generic_investment_thesis": _fail_count("investment_without_thesis"),
        "generic_research_answer": _fail_count("research_without_research"),
        "industry_refusal": _fail_count("industry_refusal"),
        "wrong_evidence": _fail_count("consensus_without_label"),
        "hallucination": _fail_count("company_without_company"),
        "recommendation_leakage": _fail_count("recommendation_leakage"),
        "unexpected_refusal": _fail_count("unexpected_refusal"),
    }
    zero_defect = all(v == 0 for v in gates.values())
    decision = "PASS" if overall >= OVERALL_TARGET_PCT and zero_defect else "FAIL"

    return {
        "suite": "answer_quality_acceptance_v1",
        "version": SUITE_VERSION,
        "total": total,
        "passed": passed,
        "overall_score": overall,
        "target_pct": OVERALL_TARGET_PCT,
        "case_pass_score": CASE_PASS_SCORE,
        "decision": decision,
        "zero_defect": zero_defect,
        "gates": gates,
        "section_scores": {k: v["pass_rate_pct"] for k, v in sorted(sections.items())},
        "section_avg_quality": {k: v["avg_score"] for k, v in sorted(sections.items())},
        "dimension_avg": dimension_avg,
        "boilerplate_clusters": clusters[:60],
        "weak_companies": weak_companies,
        "worst_answers": [
            {
                "id": r["id"],
                "section": r["section"],
                "question": r["question"],
                "score": r["score"],
                "fails": r["fails"],
                "answer": r["answer"][:220],
            }
            for r in weak_questions
        ],
        "sections": sections,
        "results": results,
    }


def _group(results: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        val = r.get(key)
        if val:
            out.setdefault(val, []).append(r)
    return out


def run(limit: Optional[int] = None) -> dict[str, Any]:
    import os

    from ask_product_test import checks
    from ask_product_test.harness import AskProductHarness

    cases = build_cases()
    if limit:
        by_section: dict[str, list[dict[str, Any]]] = {}
        for case in cases:
            by_section.setdefault(case["section"], []).append(case)
        per = max(1, limit // max(1, len(by_section)))
        cases = [c for group in by_section.values() for c in group[:per]]

    harness = AskProductHarness(
        latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000")
    )
    results: list[dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        transport = harness.ask(case["question"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        text = checks.extract_answer_text(payload) if payload else ""
        identity = None
        if case.get("ticker"):
            try:
                from company_identity.service import identity_for

                ident = identity_for(case["ticker"])
                identity = ident if ident.resolved else None
            except Exception:
                identity = None
        dims, fails = _score_case(case, text, payload, identity)
        score = _weighted(dims)
        results.append(
            {
                "id": case["id"],
                "section": case["section"],
                "question": case["question"],
                "company": case.get("company"),
                "ticker": case.get("ticker"),
                "intent": str(payload.get("intent") or ""),
                "score": score,
                "dimensions": dims,
                "fails": fails,
                "passed": score >= CASE_PASS_SCORE and not fails,
                "latency_ms": int(transport.get("latency_ms") or 0),
                "answer": text or "",
            }
        )
        if i % 50 == 0:
            print(f"  … {i}/{len(cases)} evaluated", flush=True)

    clusters = detect_boilerplate(results)
    # Boilerplate is an automatic fail — apply after cluster detection.
    for r in results:
        if r.get("boilerplate_with"):
            if "boilerplate" not in r["fails"]:
                r["fails"].append("boilerplate")
            r["passed"] = False
    for r in results:
        r["answer"] = r["answer"][:600]
    return summarise(results, clusters)
