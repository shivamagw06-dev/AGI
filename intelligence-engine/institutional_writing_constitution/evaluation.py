"""Writing Evaluation Suite — 100 benchmark investment questions for release scoring."""

from __future__ import annotations

from typing import Any

from institutional_writing_constitution.schema import EVALUATION_DIMENSIONS, INSTITUTIONAL_READABILITY_DIMENSIONS

# Core benchmark set — user-provided exemplars
_CORE_BENCHMARKS: tuple[dict[str, Any], ...] = (
    {"id": "WES_001", "question": "Should I invest in TCS?", "category": "investment_assessment", "ticker": "TCS"},
    {"id": "WES_002", "question": "Why is Titan valued at a premium?", "category": "valuation", "ticker": "TITAN"},
    {"id": "WES_003", "question": "Is HDFC Bank losing its competitive advantage?", "category": "business_quality", "ticker": "HDFCBANK"},
    {"id": "WES_004", "question": "Explain Infosys's AI strategy.", "category": "business_quality", "ticker": "INFY"},
    {"id": "WES_005", "question": "Compare Asian Paints vs Berger Paints.", "category": "peer_comparison", "ticker": "ASIANPAINT"},
    {"id": "WES_006", "question": "What changed after Reliance's latest earnings?", "category": "earnings_analysis", "ticker": "RELIANCE"},
    {"id": "WES_007", "question": "Is ITC's dividend sustainable?", "category": "financial_analysis", "ticker": "ITC"},
    {"id": "WES_008", "question": "What are the key risks in investing in Adani Enterprises?", "category": "risk_analysis", "ticker": "ADANIENT"},
    {"id": "WES_009", "question": "How does Bajaj Finance compare to HDFC Bank on growth?", "category": "peer_comparison", "ticker": "BAJFINANCE"},
    {"id": "WES_010", "question": "Is the current Nifty valuation expensive?", "category": "market_overview", "ticker": None},
    {"id": "WES_011", "question": "Should I buy Kotak Mahindra Bank at current levels?", "category": "investment_assessment", "ticker": "KOTAKBANK"},
    {"id": "WES_012", "question": "Explain HUL's volume growth challenges.", "category": "earnings_analysis", "ticker": "HINDUNILVR"},
    {"id": "WES_013", "question": "What is the investment case for Larsen & Toubro?", "category": "investment_assessment", "ticker": "LT"},
    {"id": "WES_014", "question": "How durable is Nestle India's pricing power?", "category": "business_quality", "ticker": "NESTLEIND"},
    {"id": "WES_015", "question": "Compare TCS vs Infosys on capital allocation.", "category": "peer_comparison", "ticker": "TCS"},
    {"id": "WES_016", "question": "What would invalidate the bull case on Titan?", "category": "thesis_change", "ticker": "TITAN"},
    {"id": "WES_017", "question": "Is Sun Pharma fairly valued?", "category": "valuation", "ticker": "SUNPHARMA"},
    {"id": "WES_018", "question": "Explain the impact of RBI policy on HDFC Bank.", "category": "macro_analysis", "ticker": "HDFCBANK"},
    {"id": "WES_019", "question": "What are the key monitoring indicators for Wipro?", "category": "monitoring", "ticker": "WIPRO"},
    {"id": "WES_020", "question": "Deep dive on Asian Paints business model.", "category": "deep_research", "ticker": "ASIANPAINT"},
)

# NIFTY 50 coverage for expanded benchmark registry
_NIFTY50_TICKERS: tuple[tuple[str, str], ...] = (
    ("RELIANCE", "Reliance Industries"),
    ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"),
    ("INFY", "Infosys"),
    ("ICICIBANK", "ICICI Bank"),
    ("HINDUNILVR", "Hindustan Unilever"),
    ("ITC", "ITC"),
    ("SBIN", "State Bank of India"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("LT", "Larsen & Toubro"),
    ("AXISBANK", "Axis Bank"),
    ("ASIANPAINT", "Asian Paints"),
    ("MARUTI", "Maruti Suzuki"),
    ("TITAN", "Titan Company"),
    ("BAJFINANCE", "Bajaj Finance"),
    ("HCLTECH", "HCL Technologies"),
    ("WIPRO", "Wipro"),
    ("ULTRACEMCO", "UltraTech Cement"),
    ("NESTLEIND", "Nestle India"),
    ("SUNPHARMA", "Sun Pharmaceutical"),
    ("POWERGRID", "Power Grid Corporation"),
    ("NTPC", "NTPC"),
    ("M&M", "Mahindra & Mahindra"),
    ("TATAMOTORS", "Tata Motors"),
    ("TECHM", "Tech Mahindra"),
    ("ADANIENT", "Adani Enterprises"),
    ("JSWSTEEL", "JSW Steel"),
    ("TATASTEEL", "Tata Steel"),
    ("INDUSINDBK", "IndusInd Bank"),
    ("BAJAJFINSV", "Bajaj Finserv"),
    ("HINDALCO", "Hindalco Industries"),
    ("GRASIM", "Grasim Industries"),
    ("DIVISLAB", "Divi's Laboratories"),
    ("CIPLA", "Cipla"),
    ("DRREDDY", "Dr Reddy's Laboratories"),
    ("EICHERMOT", "Eicher Motors"),
    ("HEROMOTOCO", "Hero MotoCorp"),
    ("BRITANNIA", "Britannia Industries"),
    ("APOLLOHOSP", "Apollo Hospitals"),
    ("COALINDIA", "Coal India"),
    ("BPCL", "BPCL"),
    ("ONGC", "ONGC"),
    ("SBILIFE", "SBI Life Insurance"),
    ("HDFCLIFE", "HDFC Life Insurance"),
    ("TATACONSUM", "Tata Consumer Products"),
    ("ADANIPORTS", "Adani Ports"),
    ("UPL", "UPL"),
    ("SHREECEM", "Shree Cement"),
    ("LTIM", "LTIMindtree"),
)


def _build_extended_benchmarks() -> tuple[dict[str, Any], ...]:
    """Generate benchmark questions to reach TARGET_BENCHMARK_COUNT."""
    items: list[dict[str, Any]] = list(_CORE_BENCHMARKS)
    idx = len(items) + 1
    templates: tuple[tuple[str, str], ...] = (
        ("investment_assessment", "What is the institutional investment case for {name}?"),
        ("business_quality", "How durable is {name}'s competitive advantage?"),
        ("valuation", "Is {name} trading at a premium or discount to history?"),
        ("earnings_analysis", "What changed after {name}'s latest earnings?"),
        ("risk_analysis", "What are the primary risks in {name}?"),
        ("monitoring", "What should investors monitor on {name} over the next year?"),
        ("thesis_change", "What evidence would invalidate the thesis on {name}?"),
        ("financial_analysis", "How sustainable is {name}'s cash generation?"),
    )
    for ticker, name in _NIFTY50_TICKERS:
        for category, template in templates:
            if idx > TARGET_BENCHMARK_COUNT:
                break
            qid = f"WES_{idx:03d}"
            if any(b["id"] == qid for b in items):
                continue
            # Skip duplicates of core questions (same ticker + similar category)
            question = template.format(name=name)
            if any(b.get("ticker") == ticker and b.get("category") == category for b in items):
                continue
            items.append({
                "id": qid,
                "question": question,
                "category": category,
                "ticker": ticker,
            })
            idx += 1
        if idx > TARGET_BENCHMARK_COUNT:
            break
    return tuple(items[:TARGET_BENCHMARK_COUNT])


TARGET_BENCHMARK_COUNT = 100

BENCHMARK_QUESTIONS: tuple[dict[str, Any], ...] = _build_extended_benchmarks()


def list_benchmark_questions(*, category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    items = list(BENCHMARK_QUESTIONS)
    if category:
        items = [q for q in items if q.get("category") == category]
    return items[:limit]


def evaluation_rubric() -> dict[str, Any]:
    return {
        "writing_score_dimensions": list(EVALUATION_DIMENSIONS),
        "institutional_readability_dimensions": list(INSTITUTIONAL_READABILITY_DIMENSIONS),
        "scale": "0-100 per dimension",
        "release_gate": "Average ≥ 75 across dimensions on benchmark sample",
        "investor_metric": "institutional_readability_score",
        "benchmark_count": len(BENCHMARK_QUESTIONS),
        "benchmark_target": TARGET_BENCHMARK_COUNT,
    }


def score_institutional_readability(pack: dict[str, Any]) -> dict[str, Any]:
    """Investor-facing readability score — the metric to show in demos."""
    validation = pack.get("writing_constitution_validation") or {}
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or {}
    plan = iwc.get("response_plan") or pack.get("response_plan") or {}

    base = 78 if validation.get("passed") else 55
    evidence = sections.get("supporting_evidence") or sections.get("what_evidence_suggests") or {}
    debate = sections.get("investment_debate") or {}
    matters = sections.get("what_matters_most") or sections.get("investment_meaning") or {}
    forbidden = len(validation.get("forbidden_hits") or [])

    scores = {
        "clarity": min(100, base + 12),
        "institutional_tone": max(0, 95 - forbidden * 15),
        "prioritization": min(100, base + (8 if plan.get("top_insights") else 0)),
        "evidence_integration": min(100, base + (14 if evidence.get("assertion_backed") else 4)),
        "narrative_flow": min(100, base + (10 if debate.get("narrative") else 5)),
        "investor_usefulness": min(100, base + (12 if matters or debate else 6)),
    }
    avg = round(sum(scores.values()) / len(scores), 1)
    return {
        "label": "Institutional Readability Score",
        "scores": scores,
        "average": avg,
        "investor_ready": avg >= 90,
        "forward_test": "Would a portfolio manager forward this to the investment committee without editing?",
    }


def score_writing_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Heuristic scoring scaffold for evaluation suite (deterministic v1)."""
    validation = pack.get("writing_constitution_validation") or {}
    iwc = pack.get("institutional_writing_constitution") or {}
    sections = iwc.get("sections") or {}

    base = 70 if validation.get("passed") else 40
    evidence = sections.get("supporting_evidence") or sections.get("what_evidence_suggests") or {}
    assertion_backed = 15 if evidence.get("assertion_backed") else 0
    exec_ok = 10 if (sections.get("executive_summary") or {}).get("word_count", 999) <= 150 else 0
    forbidden = len(validation.get("forbidden_hits") or [])

    scores = {
        "executive_summary_quality": min(100, base + exec_ok),
        "institutional_tone": max(0, 90 - forbidden * 20),
        "clarity": min(100, base + 10),
        "evidence_usage": min(100, base + assertion_backed),
        "prioritization": min(100, base + (8 if sections.get("what_matters_most") else 5)),
        "implication_explanation": min(100, base + (10 if sections.get("investment_debate") else 0)),
        "uncertainty_handling": min(100, base + (10 if sections.get("key_uncertainties") else 0)),
        "readability": min(100, base + 8),
    }
    avg = round(sum(scores.values()) / len(scores), 1)
    return {
        "scores": scores,
        "average": avg,
        "passed_release_gate": avg >= 75,
    }
