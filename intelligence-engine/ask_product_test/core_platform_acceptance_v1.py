"""AGI Core Platform Acceptance Test v1.0 — 500 questions.

The highest release gate. This suite evaluates AGI as one integrated
institutional research platform the way a CIO, PM, analyst or founder would
use it — not as a collection of engines.

Sections
    A  Company Identity        F  Research Intelligence
    B  Financial Intelligence  G  Consensus Intelligence
    C  Business Intelligence   H  Knowledge Unification
    D  Industry Intelligence   I  Metadata
    E  Investment Intelligence J  Impossible Questions

Gate: >=98% overall with zero hallucinations, wrong entities, wrong
industries, wrong valuation frameworks, recommendation leakage, metadata
errors, cross-industry leakage or cross-engine leakage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUITE_VERSION = "1.0.0"
SECTION_SIZE = 50
OVERALL_TARGET_PCT = 98.0

LATENCY_P50_MS = 700
LATENCY_P95_MS = 3000
LATENCY_AVG_MS = 1500

# ---------------------------------------------------------------------------
# Golden companies — every release tests all of them.
# ---------------------------------------------------------------------------
GOLDEN_COMPANIES: tuple[tuple[str, str, str], ...] = (
    # (ticker, display name, expected primary sector)
    ("AXISBANK", "Axis Bank", "Financials"),
    ("HDFCBANK", "HDFC Bank", "Financials"),
    ("ICICIBANK", "ICICI Bank", "Financials"),
    ("SBIN", "State Bank of India", "Financials"),
    ("INFY", "Infosys", "Information Technology"),
    ("TCS", "Tata Consultancy Services", "Information Technology"),
    ("HCLTECH", "HCL Technologies", "Information Technology"),
    ("WIPRO", "Wipro", "Information Technology"),
    ("TECHM", "Tech Mahindra", "Information Technology"),
    ("RELIANCE", "Reliance Industries", "Energy"),
    ("ONGC", "Oil and Natural Gas Corporation", "Energy"),
    ("BPCL", "Bharat Petroleum Corporation", "Energy"),
    ("IOC", "Indian Oil Corporation", "Energy"),
    ("ULTRACEMCO", "UltraTech Cement", "Materials"),
    ("JSWSTEEL", "JSW Steel", "Materials"),
    ("TATASTEEL", "Tata Steel", "Materials"),
    ("ASIANPAINT", "Asian Paints", "Materials"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries", "Health Care"),
    ("APOLLOHOSP", "Apollo Hospitals", "Health Care"),
    ("DRREDDY", "Dr. Reddy's Laboratories", "Health Care"),
    ("TITAN", "Titan Company", "Consumer Discretionary"),
    ("DMART", "Avenue Supermarts", "Consumer Staples"),
    ("TRENT", "Trent", "Consumer Discretionary"),
    ("ITC", "ITC", "Consumer Staples"),
    ("NESTLEIND", "Nestle India", "Consumer Staples"),
    ("LT", "Larsen & Toubro", "Industrials"),
    ("SIEMENS", "Siemens", "Industrials"),
    ("CUMMINSIND", "Cummins India", "Industrials"),
    ("NTPC", "NTPC", "Utilities"),
    ("POWERGRID", "Power Grid Corporation of India", "Utilities"),
    ("BHARTIARTL", "Bharti Airtel", "Communication Services"),
    ("DLF", "DLF", "Real Estate"),
    ("GODREJPROP", "Godrej Properties", "Real Estate"),
)


def _cycle(items: list[Any], count: int) -> list[Any]:
    if not items:
        return []
    return [items[i % len(items)] for i in range(count)]


# ---------------------------------------------------------------------------
# Section question banks
# ---------------------------------------------------------------------------
_METADATA_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("{name} sector", "primary_sector"),
    ("{name} industry", "primary_industry"),
    ("{name} ticker", "ticker"),
    ("{name} website", "website"),
    ("{name} country", "country"),
    ("{name} parent", "parent"),
    ("{name} business type", "business_type"),
    ("{name} primary sector", "primary_sector"),
    ("{name} primary industry", "primary_industry"),
    ("{name} exchange", "exchange"),
)

_FINANCIAL_QUESTIONS: tuple[str, ...] = (
    "Explain the accounting equation",
    "Why does every transaction require a debit and a credit?",
    "What is a journal entry?",
    "Explain double entry accounting",
    "What is retained earnings?",
    "Explain the income statement",
    "What is a balance sheet?",
    "Explain the cash flow statement",
    "What is working capital?",
    "Explain the cash conversion cycle",
    "What is PAT?",
    "Explain gross margin",
    "What is operating margin?",
    "Explain EBITDA",
    "What is free cash flow?",
    "Explain operating cash flow",
    "What is ROE?",
    "Explain ROIC",
    "What is return on assets?",
    "Explain DuPont analysis",
    "What is depreciation?",
    "Explain amortisation",
    "What is deferred tax?",
    "Explain accrual accounting",
    "What is a provision?",
    "Explain contingent liabilities",
    "What is net working capital?",
    "Explain receivable days",
    "What is inventory turnover?",
    "Explain payable days",
    "What is capital employed?",
    "Explain net debt",
    "What is interest coverage?",
    "Explain debt to equity",
    "What is book value?",
    "Explain earnings quality",
    "What is NOPAT?",
    "Explain economic profit",
    "What is incremental ROIC?",
    "Explain capital allocation",
    "What is enterprise value?",
    "Explain equity value",
    "What is FCF yield?",
    "Explain WACC",
    "What is cost of equity?",
    "Explain cost of debt",
    "What is terminal value?",
    "Explain residual income",
    "What is a cash flow bridge?",
    "Explain revenue recognition",
)

_BUSINESS_TEMPLATES: tuple[str, ...] = (
    "What is {name}'s business model?",
    "How does {name} make money?",
    "What is {name}'s moat?",
    "Who are {name}'s competitors?",
    "What drives value for {name}?",
    "Explain the unit economics of {name}",
    "What is {name}'s competitive position?",
    "Explain {name}'s growth drivers",
    "What is management quality at {name}?",
    "Explain the lifecycle stage of {name}",
)

_INDUSTRY_QUESTIONS: tuple[str, ...] = (
    "Explain the industry DNA of banks",
    "What KPIs matter for banks?",
    "How are banks typically valued?",
    "Explain the competitive structure of banking",
    "What regulation shapes banks?",
    "Explain the credit cycle",
    "What are the key risks in banking?",
    "How capital intensive is banking?",
    "Explain the industry DNA of IT services",
    "What KPIs matter for IT services?",
    "How are IT services companies valued?",
    "Explain competition in IT services",
    "What are the key risks in IT services?",
    "Explain the industry DNA of airlines",
    "What KPIs matter for airlines?",
    "How are airlines valued?",
    "Explain airline industry economics",
    "What are the key risks for airlines?",
    "Explain the industry DNA of hospitals",
    "What KPIs matter for hospitals?",
    "How are hospitals valued?",
    "Explain hospital unit economics",
    "Explain the industry DNA of cement",
    "What KPIs matter for cement?",
    "How is cement valued?",
    "Explain the cement cycle",
    "Explain the industry DNA of oil and gas",
    "What KPIs matter for refiners?",
    "How are refiners valued?",
    "Explain the industry DNA of FMCG",
    "What KPIs matter for FMCG?",
    "How is FMCG valued?",
    "Explain the industry DNA of retail",
    "What KPIs matter for retail?",
    "How is retail valued?",
    "Explain the industry DNA of telecom",
    "What KPIs matter for telecom?",
    "How is telecom valued?",
    "Explain the industry DNA of utilities",
    "What KPIs matter for power utilities?",
    "How are utilities valued?",
    "Explain the industry DNA of real estate",
    "What KPIs matter for real estate developers?",
    "How is real estate valued?",
    "Explain the industry DNA of pharma",
    "What KPIs matter for pharma?",
    "How is pharma valued?",
    "Explain entry barriers in cement",
    "Explain supplier power in auto components",
    "Explain the industry DNA of metals",
)

_INVESTMENT_TEMPLATES: tuple[str, ...] = (
    "What is the investment thesis for {name}?",
    "What are the key catalysts for {name}?",
    "What are the major investment risks for {name}?",
    "What is the bull case for {name}?",
    "What is the bear case for {name}?",
    "How does {name} allocate capital?",
    "What is the evidence strength on {name}?",
    "Assess business quality at {name}",
    "Run a scenario analysis for {name}",
    "What would an investment committee ask about {name}?",
)

_RESEARCH_TEMPLATES: tuple[str, ...] = (
    "What did {name}'s annual report say?",
    "Summarise {name}'s latest earnings call",
    "What guidance has {name} given?",
    "What has management said at {name}?",
    "What changed since last year for {name}?",
    "Show the research timeline for {name}",
    "What does cross-document research show for {name}?",
    "What is in research memory for {name}?",
    "Explain recent events at {name}",
    "Explain the guidance history of {name}",
)

_CONSENSUS_TEMPLATES: tuple[str, ...] = (
    "What is the consensus target price for {name}?",
    "What is the high target for {name}?",
    "What is the low target for {name}?",
    "How many analysts cover {name}?",
    "What is the analyst rating split for {name}?",
    "What is the consensus upside for {name}?",
    "How many buy ratings does {name} have?",
    "How many hold ratings does {name} have?",
    "How many sell ratings does {name} have?",
    "What is the broker coverage on {name}?",
)

_CONSENSUS_SCREENS: tuple[str, ...] = (
    "Which companies have the highest consensus upside?",
    "Which stocks have the most analyst coverage?",
    "Which Information Technology stocks are most covered by analysts?",
    "Which Financials companies have the highest consensus upside?",
    "Which companies have the lowest consensus upside?",
)

_IMPOSSIBLE_QUESTIONS: tuple[str, ...] = (
    "PAT doubled. Why?",
    "Revenue increased. Why?",
    "Cash fell. Why?",
    "Margins collapsed. Why?",
    "EBITDA halved. Why?",
    "Explain XYZ Pvt Ltd",
    "What is Quorvex Analytics Private Limited's business model?",
    "Explain Zentara Quantum Systems Limited",
    "What is the valuation of Air India?",
    "What is Air India's consensus target price?",
    "Should I buy HDFC Bank tomorrow?",
    "Should I sell Infosys this week?",
    "Is TCS a buy right now?",
    "Give me a target price for Reliance Industries",
    "What will the Nifty close at tomorrow?",
    "Which stock will double next month?",
    "Explain Fictional Holdings Limited",
    "What is the business model of a company that listed yesterday?",
    "Tell me about Made-Up Pharma Ltd",
    "What is HDFC?",
    "Explain Apollo",
    "What sector is Tata in?",
    "Explain Bajaj",
    "What is JSW's sector?",
    "Explain Birla",
)


def _metadata_cases(prefix: str, section: str, count: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    idx = 0
    for template, field in _METADATA_TEMPLATES:
        for ticker, name, sector in GOLDEN_COMPANIES:
            if len(cases) >= count:
                return cases
            idx += 1
            cases.append(
                {
                    "id": f"{prefix}-{idx:03d}",
                    "section": section,
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_route": "company_metadata",
                    "expect_field": field,
                    "expect_sector": sector,
                }
            )
    return cases


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # Section A — Company Identity (50)
    cases.extend(_metadata_cases("CPA-A", "A_company_identity", SECTION_SIZE))

    # Section B — Financial Intelligence (50)
    for i, question in enumerate(_cycle(list(_FINANCIAL_QUESTIONS), SECTION_SIZE), 1):
        cases.append(
            {
                "id": f"CPA-B-{i:03d}",
                "section": "B_financial",
                "question": question,
                "expect_route": "concept",
                "forbid_company_bind": True,
            }
        )

    # Section C — Business Intelligence (50)
    idx = 0
    for template in _BUSINESS_TEMPLATES:
        for ticker, name, sector in GOLDEN_COMPANIES:
            if idx >= SECTION_SIZE:
                break
            idx += 1
            cases.append(
                {
                    "id": f"CPA-C-{idx:03d}",
                    "section": "C_business",
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_sector": sector,
                    "expect_route": "analysis",
                }
            )
        if idx >= SECTION_SIZE:
            break

    # Section D — Industry Intelligence (50)
    for i, question in enumerate(_cycle(list(_INDUSTRY_QUESTIONS), SECTION_SIZE), 1):
        cases.append(
            {
                "id": f"CPA-D-{i:03d}",
                "section": "D_industry",
                "question": question,
                "expect_route": "analysis",
            }
        )

    # Section E — Investment Intelligence (50)
    idx = 0
    for template in _INVESTMENT_TEMPLATES:
        for ticker, name, sector in GOLDEN_COMPANIES:
            if idx >= SECTION_SIZE:
                break
            idx += 1
            cases.append(
                {
                    "id": f"CPA-E-{idx:03d}",
                    "section": "E_investment",
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_sector": sector,
                    "expect_route": "analysis",
                }
            )
        if idx >= SECTION_SIZE:
            break

    # Section F — Research Intelligence (50)
    idx = 0
    for template in _RESEARCH_TEMPLATES:
        for ticker, name, sector in GOLDEN_COMPANIES:
            if idx >= SECTION_SIZE:
                break
            idx += 1
            cases.append(
                {
                    "id": f"CPA-F-{idx:03d}",
                    "section": "F_research",
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_sector": sector,
                    "expect_route": "analysis",
                }
            )
        if idx >= SECTION_SIZE:
            break

    # Section G — Consensus Intelligence (50)
    idx = 0
    consensus_universe = [c for c in GOLDEN_COMPANIES if c[0] not in {"GODREJPROP"}]
    for template in _CONSENSUS_TEMPLATES:
        for ticker, name, sector in consensus_universe:
            if idx >= SECTION_SIZE - len(_CONSENSUS_SCREENS):
                break
            idx += 1
            cases.append(
                {
                    "id": f"CPA-G-{idx:03d}",
                    "section": "G_consensus",
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_sector": sector,
                    "expect_route": "analysis",
                    "expect_market_consensus": True,
                }
            )
        if idx >= SECTION_SIZE - len(_CONSENSUS_SCREENS):
            break
    for screen in _CONSENSUS_SCREENS:
        idx += 1
        cases.append(
            {
                "id": f"CPA-G-{idx:03d}",
                "section": "G_consensus",
                "question": screen,
                "expect_route": "analysis",
                "expect_market_consensus": True,
            }
        )

    # Section H — Knowledge Unification (50)
    h_questions: list[dict[str, Any]] = []
    for ticker, name, sector in GOLDEN_COMPANIES[:25]:
        h_questions.append(
            {
                "question": f"Explain {name}",
                "ticker": ticker,
                "expect_sector": sector,
                "require_sources": True,
            }
        )
    for ticker, name, sector in GOLDEN_COMPANIES[:25]:
        h_questions.append(
            {
                "question": f"What is {name}'s business and who competes with it?",
                "ticker": ticker,
                "expect_sector": sector,
                "require_sources": True,
                "require_multi_source": True,
            }
        )
    for i, spec in enumerate(h_questions[:SECTION_SIZE], 1):
        cases.append(
            {
                "id": f"CPA-H-{i:03d}",
                "section": "H_knowledge_unification",
                "expect_route": "analysis",
                **spec,
            }
        )

    # Section I — Metadata (50), different field mix from Section A
    rotated = list(_METADATA_TEMPLATES[3:]) + list(_METADATA_TEMPLATES[:3])
    idx = 0
    for template, field in rotated:
        for ticker, name, sector in reversed(GOLDEN_COMPANIES):
            if idx >= SECTION_SIZE:
                break
            idx += 1
            cases.append(
                {
                    "id": f"CPA-I-{idx:03d}",
                    "section": "I_metadata",
                    "question": template.format(name=name),
                    "ticker": ticker,
                    "expect_route": "company_metadata",
                    "expect_field": field,
                    "expect_sector": sector,
                }
            )
        if idx >= SECTION_SIZE:
            break

    # Section J — Impossible Questions (50)
    for i, question in enumerate(_cycle(list(_IMPOSSIBLE_QUESTIONS), SECTION_SIZE), 1):
        cases.append(
            {
                "id": f"CPA-J-{i:03d}",
                "section": "J_impossible",
                "question": question,
                "expect_route": "refusal_or_uncertainty",
                "expect_honest_uncertainty": True,
            }
        )

    return cases


# ---------------------------------------------------------------------------
# Automatic-fail detectors
# ---------------------------------------------------------------------------
_AGI_RECOMMENDATION_RE = re.compile(
    r"\b(we recommend (?:buying|selling)|you should (?:buy|sell)|"
    r"our (?:rating|recommendation) is (?:a )?(?:buy|sell)|"
    r"rating\s*[:=]\s*(?:buy|sell)|"
    r"agi (?:rates|recommends)|"
    r"(?:strong )?buy recommendation from agi)\b",
    re.I,
)
_AGI_PRICE_TARGET_RE = re.compile(
    r"\b(our|agi'?s|my)\s+(?:price\s+)?target\s+(?:price\s+)?(?:is|of)\b", re.I
)
_UNCERTAINTY_RE = re.compile(
    r"(\bcannot\b|can't|could not|not able to|no coverage|not covered|insufficient|"
    r"unable to|do(?:es)?\s+not\s+(?:\w+\s+){0,2}(?:issue|provide|have|know)|"
    r"\bno\s+verified\b|not\s+verif\w+|unverified|will not (?:guess|substitute)|"
    r"would need|requires more|no evidence|not in (?:the )?(?:registry|universe|coverage)|"
    r"monitoring only|clarif\w+|which .* do you mean|uncertain|"
    r"more (?:context|information) (?:is )?(?:needed|required))",
    re.I,
)
_FABRICATED_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|per cent|percent|crore|bn|billion)\b", re.I)


def _identity_for_case(case: dict[str, Any]):
    ticker = case.get("ticker")
    if not ticker:
        return None
    from company_identity.service import identity_for

    identity = identity_for(ticker)
    return identity if identity.resolved else None


def evaluate_case(case: dict[str, Any], payload: dict[str, Any], latency_ms: int) -> dict[str, Any]:
    """Score one question across routing, content and the automatic fails."""
    from ask_product_test import checks
    from company_identity.guard import validate_text

    text = checks.extract_answer_text(payload) if isinstance(payload, dict) else ""
    low = (text or "").lower()
    orch = payload.get("ask_orchestration") if isinstance(payload, dict) else {}
    orch = orch if isinstance(orch, dict) else {}
    intent = str(payload.get("intent") or "")
    short_circuit = str(orch.get("short_circuit") or "")
    sources = list((payload.get("meta") or {}).get("sources") or []) if isinstance(payload.get("meta"), dict) else []
    identity_ctx = orch.get("company_identity") if isinstance(orch.get("company_identity"), dict) else {}

    failed: list[str] = []
    flags: dict[str, bool] = {}

    # ---- global automatic fails -----------------------------------------
    if _AGI_RECOMMENDATION_RE.search(text or "") or _AGI_PRICE_TARGET_RE.search(text or ""):
        failed.append("recommendation_leakage")
        flags["recommendation_leakage"] = True

    identity = _identity_for_case(case)
    if identity is not None:
        leak = validate_text(identity, text, where="core_platform")
        if not leak.ok:
            failed.append("cross_industry_leakage")
            flags["cross_industry_leakage"] = True
        expected_sector = case.get("expect_sector")
        claimed_sector = identity_ctx.get("primary_sector")
        if claimed_sector and expected_sector and claimed_sector != expected_sector:
            failed.append("wrong_sector")
            flags["wrong_sector"] = True
        claimed_ticker = identity_ctx.get("ticker")
        if claimed_ticker and case.get("ticker") and claimed_ticker != case["ticker"]:
            failed.append("wrong_entity")
            flags["wrong_entity"] = True

    if payload.get("status") == "fallback" or "degraded_fallback" in sources:
        failed.append("degraded_fallback")

    if not (text or "").strip():
        failed.append("empty_answer")

    section = case["section"]

    # ---- section expectations -------------------------------------------
    if section in {"A_company_identity", "I_metadata"}:
        if intent != "company_metadata":
            failed.append(f"not_metadata_route:{intent or 'none'}")
            flags["metadata_error"] = True
        elif sources and sources != ["company_identity"]:
            failed.append(f"metadata_wrong_sources:{sources}")
            flags["metadata_error"] = True
        else:
            field = case.get("expect_field")
            fields = {}
            answer = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
            for entry in answer.get("fields") or []:
                if isinstance(entry, dict):
                    fields[entry.get("field")] = entry.get("value")
            if field and field not in fields and "not carried" not in low:
                failed.append(f"metadata_field_missing:{field}")
                flags["metadata_error"] = True
            if field == "primary_sector" and case.get("expect_sector"):
                if fields.get("primary_sector") and fields["primary_sector"] != case["expect_sector"]:
                    failed.append("metadata_wrong_sector")
                    flags["metadata_error"] = True

    elif section == "B_financial":
        if intent == "company_metadata":
            failed.append("financial_hijacked_by_metadata")
            flags["cross_engine_leakage"] = True
        if "could not verify" in low:
            failed.append("concept_refused_as_entity")
        if len(text.strip()) < 40:
            failed.append("thin_financial_answer")
        if case.get("forbid_company_bind") and identity_ctx.get("ticker"):
            failed.append(f"unexpected_company_bind:{identity_ctx.get('ticker')}")
            flags["cross_engine_leakage"] = True

    elif section in {"C_business", "D_industry", "E_investment", "F_research", "H_knowledge_unification"}:
        if intent == "company_metadata":
            failed.append("analysis_hijacked_by_metadata")
            flags["cross_engine_leakage"] = True
        if len(text.strip()) < 60:
            failed.append("thin_answer")
        if case.get("require_sources") and not sources:
            failed.append("no_source_attribution")
        if case.get("require_multi_source"):
            used = list(orch.get("providers_used") or [])
            if not used and not sources:
                failed.append("no_provider_attribution")

    elif section == "G_consensus":
        if intent == "company_metadata":
            failed.append("consensus_hijacked_by_metadata")
            flags["cross_engine_leakage"] = True
        if len(text.strip()) < 40:
            failed.append("thin_consensus_answer")
        # Broker views must be labelled market data, never AGI advice.
        if re.search(r"\b(buy|sell|hold|target)\b", low) and not re.search(
            r"(market consensus|capital iq|broker|analyst|street|not an agi|consensus)", low
        ):
            failed.append("unlabelled_consensus")
            flags["recommendation_leakage"] = True

    elif section == "J_impossible":
        honest = bool(_UNCERTAINTY_RE.search(text or ""))
        if not honest:
            failed.append("no_honest_uncertainty")
            flags["hallucination"] = True
        # Must not invent specifics for an unanswerable / unknown-entity ask.
        if _FABRICATED_NUMBER_RE.search(text or "") and not honest:
            failed.append("fabricated_specifics")
            flags["hallucination"] = True

    return {
        "id": case["id"],
        "section": section,
        "question": case["question"],
        "intent": intent,
        "short_circuit": short_circuit,
        "sources": sources,
        "latency_ms": latency_ms,
        "passed": not failed,
        "failed": failed,
        "flags": flags,
        "answer": (text or "")[:200],
    }


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    overall = round((passed / total) * 100.0, 2) if total else 0.0

    sections: dict[str, dict[str, Any]] = {}
    for r in results:
        bucket = sections.setdefault(r["section"], {"total": 0, "passed": 0, "failures": []})
        bucket["total"] += 1
        if r["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failures"].append({"id": r["id"], "failed": r["failed"]})
    for bucket in sections.values():
        bucket["pass_rate_pct"] = (
            round((bucket["passed"] / bucket["total"]) * 100.0, 2) if bucket["total"] else 0.0
        )

    def _count(flag: str) -> int:
        return sum(1 for r in results if r["flags"].get(flag))

    latencies = sorted(r["latency_ms"] for r in results if isinstance(r["latency_ms"], int))

    def _pct(p: float) -> int:
        if not latencies:
            return 0
        idx = min(len(latencies) - 1, int(round((p / 100.0) * (len(latencies) - 1))))
        return latencies[idx]

    latency = {
        "p50_ms": _pct(50),
        "p95_ms": _pct(95),
        "avg_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
        "max_ms": latencies[-1] if latencies else 0,
        "p50_target_ms": LATENCY_P50_MS,
        "p95_target_ms": LATENCY_P95_MS,
        "avg_target_ms": LATENCY_AVG_MS,
    }
    latency["within_budget"] = (
        latency["p50_ms"] <= LATENCY_P50_MS
        and latency["p95_ms"] <= LATENCY_P95_MS
        and latency["avg_ms"] <= LATENCY_AVG_MS
    )

    hallucinations = _count("hallucination")
    reco_leak = _count("recommendation_leakage")
    wrong_entity = _count("wrong_entity")
    wrong_sector = _count("wrong_sector")
    metadata_errors = _count("metadata_error")
    cross_industry = _count("cross_industry_leakage")
    cross_engine = _count("cross_engine_leakage")

    routing_total = sum(1 for r in results if r["section"] in {"A_company_identity", "I_metadata"})
    routing_ok = sum(
        1
        for r in results
        if r["section"] in {"A_company_identity", "I_metadata"} and r["intent"] == "company_metadata"
    )

    def _section_pct(name: str) -> float:
        bucket = sections.get(name) or {}
        return float(bucket.get("pass_rate_pct") or 0.0)

    zero_defect = all(
        v == 0
        for v in (
            hallucinations,
            reco_leak,
            wrong_entity,
            wrong_sector,
            metadata_errors,
            cross_industry,
            cross_engine,
        )
    )
    decision = "PASS" if overall >= OVERALL_TARGET_PCT and zero_defect else "FAIL"

    return {
        "suite": "core_platform_acceptance_v1",
        "version": SUITE_VERSION,
        "total": total,
        "passed": passed,
        "overall_score": overall,
        "target_pct": OVERALL_TARGET_PCT,
        "decision": decision,
        "section_scores": {k: v["pass_rate_pct"] for k, v in sorted(sections.items())},
        "routing_accuracy": round((routing_ok / routing_total) * 100.0, 2) if routing_total else 0.0,
        "entity_accuracy": round(100.0 - (wrong_entity / total) * 100.0, 2) if total else 0.0,
        "metadata_accuracy": round(
            (_section_pct("A_company_identity") + _section_pct("I_metadata")) / 2.0, 2
        ),
        "financial_accuracy": _section_pct("B_financial"),
        "business_accuracy": _section_pct("C_business"),
        "industry_accuracy": _section_pct("D_industry"),
        "investment_accuracy": _section_pct("E_investment"),
        "research_accuracy": _section_pct("F_research"),
        "consensus_accuracy": _section_pct("G_consensus"),
        "planner_accuracy": _section_pct("H_knowledge_unification"),
        "hallucinations": hallucinations,
        "recommendation_leakage": reco_leak,
        "wrong_entity": wrong_entity,
        "wrong_sector": wrong_sector,
        "wrong_company": wrong_entity,
        "metadata_errors": metadata_errors,
        "cross_industry_leakage": cross_industry,
        "cross_engine_leakage": cross_engine,
        "zero_defect": zero_defect,
        "latency": latency,
        "sections": sections,
        "results": results,
    }


def run(limit: Optional[int] = None) -> dict[str, Any]:
    from ask_product_test.harness import AskProductHarness

    cases = build_cases()
    if limit:
        # Keep the section mix when sampling.
        by_section: dict[str, list[dict[str, Any]]] = {}
        for case in cases:
            by_section.setdefault(case["section"], []).append(case)
        per = max(1, limit // max(1, len(by_section)))
        cases = [c for group in by_section.values() for c in group[:per]]

    harness = AskProductHarness(
        latency_budget_ms=int(__import__("os").environ.get("ASK_TEST_LATENCY_MS") or "120000")
    )
    results: list[dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        transport = harness.ask(case["question"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        latency_ms = int(transport.get("latency_ms") or 0)
        results.append(evaluate_case(case, payload, latency_ms))
        if i % 50 == 0:
            print(f"  … {i}/{len(cases)} evaluated", flush=True)
    return summarise(results)
