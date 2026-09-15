"""IB-01 — AGIB Institutional Benchmark constants.

Can AGIB produce institutional-grade research comparable to Bloomberg,
Capital IQ, FactSet, AlphaSense, and sell-side research?

Distinct from:
- PAT-01 (software works)
- IBS-01 (permanent sector case corpus)
"""

from __future__ import annotations

IB_WORKSTREAM_ID = "IB-01"
IB_01_ID = IB_WORKSTREAM_ID
IB_PRODUCT = "AGIB Institutional Benchmark"
IB_VERSION = "ib-01-v1.0.0"
IB_SPEC = "docs/AGI_IB_01_INSTITUTIONAL_BENCHMARK.md"
IB_ROLE = "competitive_intelligence_benchmark"
BENCHMARK_ENGINE_VERSION = "ib-01-grade-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"
AGIB_GENERAL_AVAILABILITY = True

GUIDING_PRINCIPLE = (
    "PAT proves the software works. IB-01 proves the investment intelligence "
    "is competitive with institutional research platforms."
)

TOTAL_POINTS = 1000
PASS_THRESHOLD = 900
INSTITUTIONAL_GRADE_LABEL = "Institutional Grade"

SECTIONS = (
    ("A", "company_research", "Company Research", 200),
    ("B", "blind_comparison", "Blind Comparison", 200),
    ("C", "hallucination", "Hallucination Test", 100),
    ("D", "speed", "Speed", 100),
    ("E", "portfolio", "Portfolio Test", 100),
    ("F", "explainability", "Explainability", 100),
    ("G", "analyst_productivity", "Analyst Productivity", 100),
    ("H", "stress_reasoning", "Stress Reasoning", 100),
)

# Section A — 20-company universe
IB_COMPANIES = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "INFY",
    "KOTAKBANK",
    "ASIANPAINT",
    "TITAN",
    "HAL",
    "DIXON",
    "TRENT",
    "ADANIPORTS",
    "ICICIBANK",
    "SBIN",
    "BHARTIARTL",
    "ITC",
    "LT",
    "MARUTI",
    "SUNPHARMA",
    "ULTRACEMCO",
    "NESTLEIND",
)

COMPANY_RESEARCH_DIMENSIONS = (
    "business_quality",
    "risks",
    "valuation",
    "catalysts",
    "evidence",
    "missing_information",
)

SECTION_A_POINTS_PER_COMPANY = 10  # 200 / 20
SECTION_A_POINTS_PER_DIMENSION = (
    SECTION_A_POINTS_PER_COMPANY / len(COMPANY_RESEARCH_DIMENSIONS)
)

BLIND_REPORT_LABELS = ("Report A", "Report B", "Report C", "Report D", "AGIB")
BLIND_SOURCES = (
    "Bloomberg Intelligence",
    "Capital IQ",
    "Morningstar",
    "Brokerage research",
    "AGIB",
)

HALLUCINATION_PROBES = (
    "Which company acquired XYZ?",
    "Why did margins improve?",
    "What did management say on the last call?",
    "What was guidance for the next fiscal year?",
    "Who is the current CFO?",
    "What was the exact EPS beat last quarter?",
    "Did the company announce a buyback this week?",
    "What is the precise capacity addition timeline?",
    "Which subsidiary contributed the most to EBIT?",
    "What did the auditor qualify?",
)

SPEED_TARGETS_MS = {
    "ask": 3000,
    "workspace": 2000,
    "publication": 5000,
}

PORTFOLIO_QUESTIONS = (
    "Largest risk?",
    "Sector concentration?",
    "Macro sensitivity?",
    "Interest-rate exposure?",
    "Currency exposure?",
)

LINEAGE_CHAIN = (
    "decision",
    "risk",
    "observation",
    "evidence",
    "raw_source",
)

PRODUCTIVITY_METRICS = (
    "completion_time",
    "confidence",
    "quality",
)

STRESS_SCENARIOS = (
    ("oil_plus_20", "Oil +20%"),
    ("fed_hike_100bps", "Fed hikes 100 bps"),
    ("inr_depreciation", "INR depreciates"),
    ("bank_npa_shock", "Bank NPA shock"),
    ("export_slowdown", "Export slowdown"),
)

COMPARATORS = (
    "Bloomberg",
    "Capital IQ",
    "FactSet",
    "AlphaSense",
    "sell-side research",
)
