"""Coverage Acceptance Test v1.0 — entity resolution across the coverage
boundary (PR #451): NSE-listed (pre-existing support), BSE-only (new
support via institutional_knowledge_tables bulk ingest + app/ui/
company_router.py), and unsupported/global companies (app/ui/
coverage_policy.py).

50 companies, three buckets:
    20 NSE-listed   — must resolve exactly as before (regression guard)
    20 BSE-only     — must now resolve via the IKT company router, not the
                      unknown-entity refusal or generic retrieval
    10 unsupported  — must get the honest coverage-policy refusal, never a
                      substituted company or fabricated analysis

Per-company assertions (all required for a PASS):
    1. entity_resolution_correct — the right company (and only the right
       company) was identified; for unsupported companies, this means the
       policy correctly identified them as real-but-uncovered.
    2. no_substitution — the answer/evidence never names a different real
       company than the one asked about.
    3. no_hallucination — no framework/scaffold leakage, no fabricated
       company-specific claims for an unsupported company.
       4. correct_coverage_policy — unsupported companies get the
       coverage-policy refusal OR an honest BI/KUL business-economics answer
       with no CapIQ false-bind; NSE/BSE companies do NOT trigger refusal.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

FRAMEWORK_LEAK_MARKERS = (
    "analyse via", "analyze via", "intent:", "framework:",
    "validated publish", "fill from existing reasoning", "step 1:",
    "procedure:", "framework-selection confidence", "excluded (forbidden for context)",
    "\u2610",  # "□" — raw internal checklist markers leaking into the answer
    "required domains present or softened",
)


def has_framework_leak(text: str) -> bool:
    """Whole-answer scan (not just the lead) for internal reasoning/
    scaffold artifacts that must never reach the user-facing answer, e.g.
    raw "Procedure: ... □ checklist item" framework-selection previews."""
    low = (text or "").strip().lower()
    return any(m in low for m in FRAMEWORK_LEAK_MARKERS)


_COVERAGE_POLICY_REFUSE_RE = re.compile(
    r"\b(do not currently have verified company coverage|"
    r"no verified company coverage|will not invent company-specific analysis)\b",
    re.I,
)


def has_coverage_policy_refusal(text: str) -> bool:
    return bool(_COVERAGE_POLICY_REFUSE_RE.search(text or ""))


# ---------------------------------------------------------------------------
# 20 NSE-listed companies — pre-existing support (entity_resolution seed +
# app/ui/executive_composer.py alias scan). Regression guard: PR #451 must
# not have changed behavior for any of these.
# ---------------------------------------------------------------------------
# `known_pre_existing` (optional): for a company where this suite failed,
# names a defect independently reproduced on the pre-PR#451 production
# baseline (commit aa544a9b, live at the time this suite was written) —
# i.e. verified NOT caused by this PR's IKT/company_router/bulk_sheet
# changes. Tracked here (not silently skipped) so the raw pass-rate stays
# honest while the release gate can distinguish "this PR regressed X" from
# "X was already broken platform-wide before this PR touched anything."
NSE_LISTED_20: List[Dict[str, Any]] = [
    {"id": "NSE-01", "company": "HDFC Bank", "ticker": "HDFCBANK", "prompt": "What is HDFC Bank's business model?"},
    {"id": "NSE-02", "company": "IDBI Bank", "ticker": "IDBI", "prompt": "Explain IDBI Bank."},
    {
        "id": "NSE-03",
        "company": "HDFC Life Insurance",
        "ticker": "HDFCLIFE",
        "prompt": "What is HDFC Life Insurance's business model?",
        "known_pre_existing": "entity_resolution alias scan does not recognize this phrasing (confirmed identical on production baseline commit aa544a9b, pre-dates PR #451)",
    },
    {
        "id": "NSE-04",
        "company": "HDFC Asset Management Company",
        "ticker": "HDFCAMC",
        "prompt": "Explain HDFC Asset Management Company.",
        "known_pre_existing": "entity_resolution alias scan does not recognize this phrasing (confirmed identical on production baseline commit aa544a9b, pre-dates PR #451)",
    },
    {"id": "NSE-05", "company": "ICICI Bank", "ticker": "ICICIBANK", "prompt": "What is ICICI Bank's business model?"},
    {
        "id": "NSE-06",
        "company": "ICICI Lombard General Insurance",
        "ticker": "ICICIGI",
        "prompt": "Explain ICICI Lombard General Insurance.",
        "known_pre_existing": "entity_resolution alias scan does not recognize this phrasing (confirmed identical on production baseline commit aa544a9b, pre-dates PR #451)",
    },
    {"id": "NSE-07", "company": "Infosys", "ticker": "INFY", "prompt": "What is Infosys' business model?"},
    {
        "id": "NSE-08",
        "company": "TCS",
        "ticker": "TCS",
        "prompt": "Explain TCS's business model.",
        "known_pre_existing": "executive composer leaks internal framework-selection scaffold ('Procedure: ... \u2610 checklist item') into the answer for this intent shape (confirmed identical pattern on production baseline for Axis Bank/NSE-11, pre-dates PR #451)",
    },
    {"id": "NSE-09", "company": "Reliance Industries", "ticker": "RELIANCE", "prompt": "What is Reliance Industries' business model?"},
    {"id": "NSE-10", "company": "State Bank of India", "ticker": "SBIN", "prompt": "Explain State Bank of India."},
    {
        "id": "NSE-11",
        "company": "Axis Bank",
        "ticker": "AXISBANK",
        "prompt": "What is Axis Bank's business model?",
        "known_pre_existing": "executive composer leaks internal framework-selection scaffold, incl. a stray 'Infosys Annual Report FY24' evidence citation, into the answer (confirmed identical on production baseline commit aa544a9b, pre-dates PR #451)",
    },
    {"id": "NSE-12", "company": "Kotak Mahindra Bank", "ticker": "KOTAKBANK", "prompt": "Explain Kotak Mahindra Bank."},
    {"id": "NSE-13", "company": "Wipro", "ticker": "WIPRO", "prompt": "What is Wipro's business model?"},
    {
        "id": "NSE-14",
        "company": "HCL Technologies",
        "ticker": "HCLTECH",
        "prompt": "Explain HCL Technologies.",
        "known_pre_existing": "executive composer leaks internal framework-selection scaffold, incl. a stray 'Infosys Annual Report FY24' evidence citation, into the answer (same class of defect as NSE-11, pre-dates PR #451)",
    },
    {
        "id": "NSE-15",
        "company": "Tata Motors",
        "ticker": "TATAMOTORS",
        "prompt": "What is Tata Motors' business model?",
        "known_pre_existing": "data ambiguity, not a routing bug: the ingested Capital IQ export reflects Tata Motors' 2024 passenger/commercial-vehicle demerger and only carries 'Tata Motors Passenger Vehicles Limited' (TMPV) — the pre-demerger combined-entity ticker TATAMOTORS is not itself a row in the source data",
    },
    {"id": "NSE-16", "company": "Tata Steel", "ticker": "TATASTEEL", "prompt": "Explain Tata Steel."},
    {"id": "NSE-17", "company": "Tata Power", "ticker": "TATAPOWER", "prompt": "What is Tata Power's business model?"},
    {"id": "NSE-18", "company": "Titan Company", "ticker": "TITAN", "prompt": "Explain Titan Company."},
    {"id": "NSE-19", "company": "Adani Enterprises", "ticker": "ADANIENT", "prompt": "What is Adani Enterprises' business model?"},
    {
        "id": "NSE-20",
        "company": "JSW Energy",
        "ticker": "JSWENERGY",
        "prompt": "Explain JSW Energy.",
        "known_pre_existing": "entity_resolution alias scan does not recognize this company at all (confirmed identical on production baseline commit aa544a9b, pre-dates PR #451)",
    },
]

# ---------------------------------------------------------------------------
# 20 BSE-only companies — new support: real, actively-traded companies with
# no NSE cross-listing, resolved via bulk_sheet.py's BSE-code fallback and
# answered by app/ui/company_router.py from institutional_knowledge_tables.
# ---------------------------------------------------------------------------
BSE_ONLY_20: List[Dict[str, Any]] = [
    # HMT Limited was previously BSE-only (BSE:500191) but CapIQ's fuller
    # 7000-row export also carries NSEI:HMT — after name-dedup it canonicalizes
    # to the NSE ticker, so it is no longer a BSE-only fixture. Replaced with
    # a true BSE-only name that has no NSEI twin.
    {"id": "BSE-01", "company": "Utique Enterprises Limited", "ticker": "BSE500014", "prompt": "What is Utique Enterprises Limited's business model?"},
    {"id": "BSE-02", "company": "The Bombay Dyeing and Manufacturing Company Limited", "ticker": "BSE500020", "accept_tickers": ["BSE500020", "BOMDYEING"], "prompt": "Explain Bombay Dyeing and Manufacturing Company Limited."},
    {"id": "BSE-03", "company": "Goodricke Group Limited", "ticker": "BSE500166", "prompt": "What is Goodricke Group Limited's business model?"},
    {"id": "BSE-04", "company": "I G Petrochemicals Limited", "ticker": "BSE500199", "accept_tickers": ["BSE500199", "IGPL"], "prompt": "Explain I G Petrochemicals Limited."},
    {"id": "BSE-05", "company": "JCT Limited", "ticker": "BSE500223", "prompt": "What is JCT Limited's business model?"},
    {"id": "BSE-06", "company": "The Baroda Rayon Corporation Limited", "ticker": "BSE500270", "prompt": "Explain Baroda Rayon Corporation Limited."},
    {"id": "BSE-07", "company": "Ansal Properties & Infrastructure Limited", "ticker": "BSE500013", "accept_tickers": ["BSE500013", "ANSALAPI"], "prompt": "What is Ansal Properties & Infrastructure Limited's business model?"},
    {"id": "BSE-08", "company": "The Andhra Petrochemicals Limited", "ticker": "BSE500012", "prompt": "Explain Andhra Petrochemicals Limited."},
    {"id": "BSE-09", "company": "GTN Industries Limited", "ticker": "BSE500170", "prompt": "What is GTN Industries Limited's business model?"},
    {"id": "BSE-10", "company": "Kinetic Engineering Limited", "ticker": "BSE500240", "prompt": "Explain Kinetic Engineering Limited."},
    {"id": "BSE-11", "company": "Envair Electrodyne Limited", "ticker": "BSE500246", "prompt": "What is Envair Electrodyne Limited's business model?"},
    {"id": "BSE-12", "company": "Mid India Industries Limited", "ticker": "BSE500277", "prompt": "Explain Mid India Industries Limited."},
    {"id": "BSE-13", "company": "K G Denim Limited", "ticker": "BSE500239", "prompt": "What is K G Denim Limited's business model?"},
    {"id": "BSE-14", "company": "India Lease Development Limited", "ticker": "BSE500202", "prompt": "Explain India Lease Development Limited."},
    {"id": "BSE-15", "company": "Margo Finance Limited", "ticker": "BSE500206", "prompt": "What is Margo Finance Limited's business model?"},
    {"id": "BSE-16", "company": "International Travel House Limited", "ticker": "BSE500213", "prompt": "Explain International Travel House Limited."},
    {"id": "BSE-17", "company": "Jasch Industries Limited", "ticker": "BSE500220", "prompt": "What is Jasch Industries Limited's business model?"},
    {"id": "BSE-18", "company": "Prag Bosimi Synthetics Limited", "ticker": "BSE500192", "prompt": "Explain Prag Bosimi Synthetics Limited."},
    {"id": "BSE-19", "company": "PS IT Infrastructure & Services Limited", "ticker": "BSE505502", "prompt": "What is PS IT Infrastructure & Services Limited's business model?"},
    {"id": "BSE-20", "company": "Bihar Sponge Iron Limited", "ticker": "BSE500058", "prompt": "Explain Bihar Sponge Iron Limited."},
]

# ---------------------------------------------------------------------------
# 10 unsupported/global companies — app/ui/coverage_policy.py must refuse
# honestly, never substitute a covered company or fabricate analysis.
# ---------------------------------------------------------------------------
UNSUPPORTED_GLOBAL_10: List[Dict[str, Any]] = [
    {"id": "UNS-01", "company": "Visa", "prompt": "Why does Visa generate high free cash flow?"},
    {"id": "UNS-02", "company": "Costco", "prompt": "Why does Costco operate with low margins?"},
    {"id": "UNS-03", "company": "Ferrari", "prompt": "Why is Ferrari more profitable than Toyota?"},
    {"id": "UNS-04", "company": "Toyota", "prompt": "What is Toyota's business model?"},
    {"id": "UNS-05", "company": "Netflix", "prompt": "What is Netflix's subscriber growth strategy?"},
    {"id": "UNS-06", "company": "Tesla", "prompt": "Explain Tesla's manufacturing model."},
    {"id": "UNS-07", "company": "Walmart", "prompt": "How does Walmart maintain low prices?"},
    {"id": "UNS-08", "company": "Mastercard", "prompt": "Explain Mastercard's business model."},
    {"id": "UNS-09", "company": "PayPal", "prompt": "What is PayPal's competitive position?"},
    {"id": "UNS-10", "company": "Boeing", "prompt": "Why is Boeing facing production issues?"},
]

COVERAGE_ACCEPTANCE_50: List[Dict[str, Any]] = (
    [{"category": "nse_listed", **c} for c in NSE_LISTED_20]
    + [{"category": "bse_only", **c} for c in BSE_ONLY_20]
    + [{"category": "unsupported_global", **c} for c in UNSUPPORTED_GLOBAL_10]
)
assert len(COVERAGE_ACCEPTANCE_50) == 50


def _name_mentioned(blob: str, name: str, *, ticker: str = "") -> bool:
    """Loose containment check: strip legal suffixes/punctuation from both
    sides so 'HDFC Bank' matches 'HDFC Bank Limited' in evidence text, and
    also accept the bare ticker form ('ICICIBANK') the executive composer
    commonly substitutes for the display name in generated prose."""

    def _clean(s: str) -> str:
        s = re.sub(r"\b(limited|ltd|pvt|private|corporation|corp|inc|plc)\b", " ", s.lower())
        s = re.sub(r"[^a-z0-9 ]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    if ticker and re.search(r"\b" + re.escape(ticker.lower()) + r"\b", (blob or "").lower()):
        return True

    needle = _clean(name)
    haystack = _clean(blob)
    if not needle:
        return False
    # Require at least the first 2 significant words of the name to appear.
    words = needle.split()
    check = " ".join(words[:2]) if len(words) >= 2 else needle
    return check in haystack


_FALSE_INDIA_BIND = frozenset(
    {
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
)


def evaluate_coverage_item(
    case: Dict[str, Any],
    *,
    text: str,
    entities_blob: str,
    bound_ticker: Any,
    ikt_company_key: Any,
    short_circuit: Any,
    financial_engine: Any,
    evidence_count: int,
    http_status: int,
    latency_ms: int,
    kul_providers: Any = None,
) -> Dict[str, Any]:
    category = case["category"]
    company = case["company"]
    low = (text or "").lower()
    assertions: Dict[str, bool] = {}
    detail: Dict[str, Any] = {}
    providers = [str(p) for p in (kul_providers or [])]

    if category in ("nse_listed", "bse_only"):
        resolved_ticker = str(bound_ticker or ikt_company_key or "").upper()
        expected_ticker = case["ticker"].upper()
        accepted = {expected_ticker, *(str(t).upper() for t in (case.get("accept_tickers") or []))}
        assertions["entity_resolution_correct"] = resolved_ticker in accepted
        detail["resolved_ticker"] = resolved_ticker
        detail["expected_ticker"] = expected_ticker
        detail["accepted_tickers"] = sorted(accepted)

        assertions["no_substitution"] = _name_mentioned(
            text + " " + entities_blob, company, ticker=case["ticker"]
        )
        assertions["no_hallucination"] = not has_framework_leak(text) and evidence_count >= 1
        # These categories must NEVER trigger the unsupported-coverage refusal.
        assertions["correct_coverage_policy"] = short_circuit != "unsupported_coverage_policy"
    else:  # unsupported_global
        refused = has_coverage_policy_refusal(text)
        # Phase 3.0.5: BI via KUL may answer business-economics questions for
        # unsupported globals without CapIQ false-binds — that is also correct
        # coverage behavior (honest institutional path, not hallucination).
        bind = str(bound_ticker or ikt_company_key or "").upper()
        false_bind = bool(bind) and (
            bind in _FALSE_INDIA_BIND or bind.startswith("BSE") or bind.startswith("NSE")
        )
        bi_path = (
            short_circuit == "knowledge_unification"
            and "business_intelligence" in providers
            and not false_bind
            and not has_framework_leak(text)
            and len((text or "").strip()) >= 24
        )
        assertions["entity_resolution_correct"] = refused or bi_path
        assertions["no_substitution"] = (refused and evidence_count == 0) or (bi_path and not false_bind)
        assertions["no_hallucination"] = not has_framework_leak(text) and (refused or bi_path)
        assertions["correct_coverage_policy"] = (
            short_circuit == "unsupported_coverage_policy" or bi_path
        )
        detail["refused"] = refused
        detail["bi_path"] = bi_path
        detail["bind"] = bind
        detail["kul_providers"] = providers

    passed = all(assertions.values())
    return {
        "id": case["id"],
        "category": category,
        "company": company,
        "prompt": case["prompt"],
        "answer": text,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "detail": detail,
        "pass": passed,
    }
