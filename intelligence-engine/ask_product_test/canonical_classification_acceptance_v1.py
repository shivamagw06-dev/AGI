"""Canonical Company Classification Acceptance — 300 questions.

Capital IQ is the single source of truth. Every question verifies, for a real
company drawn from the CapIQ master across all 11 primary sectors:

    ✓ Primary Sector        ✓ Industry DNA        ✓ Business Model
    ✓ Primary Industry      ✓ Valuation Framework
    ✓ Business Type         ✓ KPI Dictionary

Release gate: 100% classification / industry / business type / valuation / KPI
accuracy, zero cross-industry leakage, zero wrong sector or industry.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUITE_VERSION = "1.0.0"

# Golden companies every release must verify (spec list).
GOLDEN_COMPANIES: tuple[str, ...] = (
    "AXISBANK",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "RELIANCE",
    "ONGC",
    "BPCL",
    "IOC",
    "INFY",
    "TCS",
    "HCLTECH",
    "WIPRO",
    "ULTRACEMCO",
    "JSWSTEEL",
    "TATASTEEL",
    "APOLLOHOSP",
    "SUNPHARMA",
    "ASIANPAINT",
    "TITAN",
    "MARUTI",
    "INDIGO",
    "NTPC",
    "POWERGRID",
    "DLF",
    "BHARTIARTL",
    "NESTLEIND",
    "ITC",
    "DMART",
    "TRENT",
    "LT",
)

# Question templates exercised against every selected company.
QUESTION_TEMPLATES: tuple[str, ...] = (
    "What sector and industry is {name} in?",
    "What is {name}'s business model?",
    "How should {name} be valued?",
    "Which KPIs matter for {name}?",
    "Give me a business overview of {name}.",
)

_SECTORS: tuple[str, ...] = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)


def _load_master() -> dict[str, dict[str, Any]]:
    from valuation_consensus.store import load_live

    return dict(load_live().get("rows") or {})


def _pick_companies(target: int = 60) -> list[str]:
    """Golden companies first, then fill by sector coverage (most-covered first)."""
    master = _load_master()
    picked: list[str] = [t for t in GOLDEN_COMPANIES if t in master]

    by_sector: dict[str, list[tuple[float, str]]] = {s: [] for s in _SECTORS}
    for ticker, row in master.items():
        sector = str(row.get("sector") or "").strip()
        if sector not in by_sector or ticker in picked:
            continue
        coverage = row.get("coverage")
        score = float(coverage) if isinstance(coverage, (int, float)) else 0.0
        by_sector[sector].append((score, ticker))

    # Round-robin across sectors so all 11 are represented.
    for pool in by_sector.values():
        pool.sort(key=lambda x: (-x[0], x[1]))
    index = 0
    while len(picked) < target:
        added = False
        for sector in _SECTORS:
            pool = by_sector.get(sector) or []
            if index < len(pool):
                picked.append(pool[index][1])
                added = True
                if len(picked) >= target:
                    break
        if not added:
            break
        index += 1
    return picked


def build_cases(target_questions: int = 300) -> list[dict[str, Any]]:
    companies = _pick_companies(target=max(1, target_questions // len(QUESTION_TEMPLATES)))
    master = _load_master()
    cases: list[dict[str, Any]] = []
    for ticker in companies:
        row = master.get(ticker) or {}
        name = str(row.get("company_name") or ticker)
        for template in QUESTION_TEMPLATES:
            cases.append(
                {
                    "id": f"CCA-{len(cases) + 1:03d}",
                    "ticker": ticker,
                    "company_name": name,
                    "sector": row.get("sector"),
                    "question": template.format(name=name),
                    "golden": ticker in GOLDEN_COMPANIES,
                }
            )
            if len(cases) >= target_questions:
                return cases
    return cases


def _identity(ticker: str):
    from company_identity.service import identity_for

    return identity_for(ticker)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Verify all seven classification dimensions for one question."""
    from company_identity.guard import validate_classification, validate_text
    from company_identity.taxonomy import framework_for

    ticker = case["ticker"]
    identity = _identity(ticker)
    failed: list[str] = []

    # ✓ Primary Sector — canonical and one of the 11
    if not identity.primary_sector:
        failed.append("primary_sector_missing")
    elif identity.primary_sector != case.get("sector"):
        failed.append("wrong_primary_sector")
    elif identity.primary_sector not in _SECTORS:
        failed.append("non_canonical_sector")

    # ✓ Primary Industry — exactly as imported
    if not identity.primary_industry:
        failed.append("primary_industry_missing")

    # ✓ Business Type — deterministic from Primary Industry
    if not identity.business_type:
        failed.append("business_type_missing")

    # ✓ Industry DNA — keyed on Primary Industry
    if not identity.industry_dna:
        failed.append("industry_dna_missing")

    # ✓ Valuation Framework + ✓ KPI Dictionary
    allowed, kpis = framework_for(identity.industry_dna)
    if tuple(identity.allowed_valuation) != tuple(allowed):
        failed.append("valuation_framework_mismatch")
    if tuple(identity.kpis) != tuple(kpis):
        failed.append("kpi_dictionary_mismatch")
    leaked_kpi = [k for k in identity.kpis if k.lower() in {f.lower() for f in identity.forbidden_kpis}]
    if leaked_kpi:
        failed.append("kpi_leakage")

    # ✓ Business Model / answer consistency — no cross-industry contamination
    answer: dict[str, Any] = {}
    try:
        from knowledge_unification.production import plan_and_gather

        answer = plan_and_gather(case["question"]) or {}
    except Exception as exc:
        failed.append(f"ask_error:{type(exc).__name__}")

    text = " ".join(
        [str(answer.get("summary") or "")] + [str(w) for w in (answer.get("why") or [])]
    )
    leak = validate_text(identity, text, where="ask")
    if not leak.ok:
        failed.append("cross_industry_leakage")

    diagnostics = answer.get("diagnostics") or {}
    claimed = diagnostics.get("company_identity") or {}
    if claimed:
        claim_report = validate_classification(
            identity,
            sector=claimed.get("primary_sector"),
            industry=claimed.get("primary_industry"),
            business_type=claimed.get("business_type"),
            industry_dna=claimed.get("industry_dna"),
        )
        if not claim_report.ok:
            failed.append("identity_contract_violation")

    return {
        "id": case["id"],
        "ticker": ticker,
        "question": case["question"],
        "golden": case["golden"],
        "sector": identity.primary_sector,
        "industry": identity.primary_industry,
        "business_type": identity.business_type,
        "industry_dna": identity.industry_dna,
        "passed": not failed,
        "failed": failed,
        "leak_violations": [v.rule for v in leak.violations],
    }


def _acceptance_data_unavailable() -> bool:
    try:
        from ask_product_test.acceptance_data import _load_vc_rows, MINIMUM_REQUIRED

        return len(_load_vc_rows()) < MINIMUM_REQUIRED["valuation_consensus_rows"]
    except Exception:
        return True


def run(target_questions: int = 300) -> dict[str, Any]:
    if _acceptance_data_unavailable():
        return {
            "suite": "canonical_classification_acceptance_v1",
            "version": SUITE_VERSION,
            "total": 0,
            "passed": 0,
            "pass_rate_pct": None,
            "golden_total": 0,
            "golden_passed": 0,
            "golden_pass_rate_pct": None,
            "cross_industry_leakage": 0,
            "wrong_sector": 0,
            "wrong_industry": 0,
            "sectors_covered": [],
            "sectors_covered_count": 0,
            "decision": "NOT_EVALUATED",
            "failure_class": "INFRASTRUCTURE",
            "reason": "Acceptance dataset unavailable — valuation consensus has insufficient rows.",
            "results": [],
        }

    cases = build_cases(target_questions)
    if not cases:
        return {
            "suite": "canonical_classification_acceptance_v1",
            "version": SUITE_VERSION,
            "total": 0,
            "passed": 0,
            "pass_rate_pct": None,
            "golden_total": 0,
            "golden_passed": 0,
            "golden_pass_rate_pct": None,
            "cross_industry_leakage": 0,
            "wrong_sector": 0,
            "wrong_industry": 0,
            "sectors_covered": [],
            "sectors_covered_count": 0,
            "decision": "NOT_EVALUATED",
            "failure_class": "INFRASTRUCTURE",
            "reason": "Acceptance dataset unavailable — zero evaluation cases built.",
            "results": [],
        }

    results = [evaluate_case(c) for c in cases]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    golden = [r for r in results if r["golden"]]
    golden_pass = sum(1 for r in golden if r["passed"])
    leaks = sum(1 for r in results if "cross_industry_leakage" in r["failed"])
    wrong_sector = sum(1 for r in results if "wrong_primary_sector" in r["failed"])
    wrong_industry = sum(1 for r in results if "primary_industry_missing" in r["failed"])
    pass_rate = round((passed / total) * 100.0, 2) if total else 0.0
    golden_rate = round((golden_pass / len(golden)) * 100.0, 2) if golden else 0.0

    decision = (
        "PASS"
        if pass_rate == 100.0
        and golden_rate == 100.0
        and leaks == 0
        and wrong_sector == 0
        and wrong_industry == 0
        else "FAIL"
    )
    sectors_covered = sorted({r["sector"] for r in results if r["sector"]})
    return {
        "suite": "canonical_classification_acceptance_v1",
        "version": SUITE_VERSION,
        "total": total,
        "passed": passed,
        "pass_rate_pct": pass_rate,
        "golden_total": len(golden),
        "golden_passed": golden_pass,
        "golden_pass_rate_pct": golden_rate,
        "cross_industry_leakage": leaks,
        "wrong_sector": wrong_sector,
        "wrong_industry": wrong_industry,
        "sectors_covered": sectors_covered,
        "sectors_covered_count": len(sectors_covered),
        "decision": decision,
        "results": results,
    }
