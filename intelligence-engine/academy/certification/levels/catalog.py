"""ACS shared level exams (1–5, 7, 9–10, 12, 15–17) + aggregator."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.levels.factory import build_concept_exams
from academy.certification.schema import ExamSpec

CONCEPTS = [
    "ROIC",
    "ROE",
    "Economic Profit",
    "Margin of Safety",
    "Capital Cycle",
    "Switching Costs",
    "Network Effects",
    "Cash Conversion Cycle",
    "Reverse DCF",
    "Cost of Equity",
    "WACC",
    "Operating Leverage",
    "Incremental ROIC",
]

CASE_HISTORY = [
    "Apple",
    "Amazon",
    "Microsoft",
    "Berkshire",
    "Nestlé",
    "Asian Paints",
    "TCS",
    "Wirecard",
    "Kodak",
    "Nokia",
    "GE",
    "Kingfisher",
    "Yes Bank",
    "IL&FS",
    "Lehman",
    "Evergrande",
]

PATTERNS = [
    "Compounder",
    "Turnaround",
    "Value Trap",
    "Capital Destroyer",
    "Platform",
    "Network Effect",
    "Commodity",
    "Negative Working Capital",
    "Premium Consumer",
    "Financial Franchise",
]


def level1_exams() -> list[ExamSpec]:
    return build_concept_exams(CONCEPTS, level=1)


def level2_exams() -> list[ExamSpec]:
    pairs = [
        ("HDFC Bank", "HDFCBANK", "Porter's Five Forces", "porter"),
        ("Nestlé India", "NESTLEIND", "Pricing Power", "pricing_power"),
        ("UltraTech Cement", "ULTRACEMCO", "Capital Cycle", "capital_cycle"),
        ("Apple", "AAPL", "Value Chain", "value_chain"),
        ("Amazon", "AMZN", "Flywheel", "flywheel"),
        ("Reliance", "RELIANCE", "Conglomerate Analysis", "conglomerate"),
    ]
    out = []
    for i, (name, ticker, fw, key) in enumerate(pairs):
        out.append(
            ExamSpec(
                exam_id=f"acs_l2_{i+1:03d}",
                level=2,
                analyst="business",
                question=f"Apply {fw} to {name}. Framework → Evidence → Reasoning → Conclusion.",
                company=name,
                ticker=ticker,
                topic=fw,
                framework=key,
                must_include=["evidence", "reasoning", "conclusion", name.split()[0].lower()],
                tags=["framework_application", key],
            )
        )
    return out


def level3_exams() -> list[ExamSpec]:
    return [
        ExamSpec(
            exam_id="acs_l3_001",
            level=3,
            analyst="valuation",
            question=(
                "Should Nestlé deserve a premium valuation? Combine Damodaran, Graham, Fisher, "
                "Klarman, Fridson and Narrative & Numbers into ONE institutional answer."
            ),
            company="Nestlé India",
            ticker="NESTLEIND",
            topic="Premium Valuation Synthesis",
            must_include=["damodaran", "graham", "fisher", "klarman", "institutional"],
            tags=["cross_book_synthesis"],
        ),
        ExamSpec(
            exam_id="acs_l3_002",
            level=3,
            analyst="valuation",
            question=(
                "Interpret high ROIC using Damodaran, Graham, Klarman, Fridson and Fisher — one unified view."
            ),
            topic="ROIC Synthesis",
            must_include=["damodaran", "graham", "klarman", "fisher", "institutional"],
            tags=["cross_book_synthesis"],
        ),
    ]


def level4_exams() -> list[ExamSpec]:
    items = [
        ("Eternal", "ETERNAL", "Does Eternal resemble Amazon or Groupon? Why?"),
        ("Apple", "AAPL", "Does Apple resemble Coca-Cola? Why?"),
        ("HDFC Bank", "HDFCBANK", "Is HDFC Bank closer to JPMorgan or Wells Fargo? Why?"),
        ("Asian Paints", "ASIANPAINT", "Can Asian Paints be compared with Sherwin-Williams? Why?"),
    ]
    out = []
    for i, (name, ticker, q) in enumerate(items):
        out.append(
            ExamSpec(
                exam_id=f"acs_l4_{i+1:03d}",
                level=4,
                analyst="business",
                question=q + " Explain similarities, differences and lessons.",
                company=name,
                ticker=ticker,
                topic="Case Transfer",
                must_include=["similar", "differ", "lesson"],
                tags=["case_transfer"],
            )
        )
    return out


def level5_exams() -> list[ExamSpec]:
    qs = [
        ("When does high ROE become misleading?", ["roe", "leverage", "misleading"]),
        ("When does high ROIC become misleading?", ["roic", "peak", "cash"]),
        ("When is PE useless?", ["pe", "earnings", "useless"]),
        ("When does DCF fail?", ["dcf", "fail", "assumption"]),
        ("When is Margin of Safety insufficient?", ["margin of safety", "insufficient", "uncertainty"]),
        ("When does EBITDA mislead?", ["ebitda", "cash", "mislead"]),
    ]
    out = []
    for i, (q, must) in enumerate(qs):
        out.append(
            ExamSpec(
                exam_id=f"acs_l5_{i+1:03d}",
                level=5,
                analyst="financial",
                question=q,
                topic="Counter Examples",
                must_include=must,
                tags=["counter_examples"],
            )
        )
    return out


def level7_exams() -> list[ExamSpec]:
    return [
        ExamSpec(
            exam_id="acs_l7_001",
            level=7,
            analyst="business",
            question=(
                "HDFC Bank long-term memory: compare current vs 2024 vs 2023. "
                "Opinion, reason, evidence, trajectory, accuracy. What changed and why?"
            ),
            company="HDFC Bank",
            ticker="HDFCBANK",
            topic="Long Term Memory",
            must_include=["previous", "updated", "changed", "trajectory", "2023", "2024"],
            tags=["memory"],
        )
    ]


def level9_exams() -> list[ExamSpec]:
    out = []
    for i, name in enumerate(CASE_HISTORY):
        out.append(
            ExamSpec(
                exam_id=f"acs_l9_{i+1:03d}",
                level=9,
                analyst="business",
                question=f"Case history: what institutional lessons does {name} teach? Pattern, failure/success modes, transferable lessons.",
                company=name,
                topic="Case History",
                must_include=[name.split()[0].lower(), "lesson", "pattern"],
                tags=["case_history"],
            )
        )
    return out


def level10_exams() -> list[ExamSpec]:
    out = []
    for i, pat in enumerate(PATTERNS):
        co = BENCHMARK_COMPANIES[i % len(BENCHMARK_COMPANIES)]
        out.append(
            ExamSpec(
                exam_id=f"acs_l10_{i+1:03d}",
                level=10,
                analyst="business",
                question=f"Pattern recognition: does {co['name']} fit the {pat} pattern? Signals, counter-signals, conclusion.",
                company=co["name"],
                ticker=co["ticker"],
                topic=pat,
                must_include=["pattern", pat.lower().split()[0], "conclusion"],
                tags=["pattern_recognition"],
            )
        )
    return out


def level12_exams() -> list[ExamSpec]:
    out = []
    for i, co in enumerate(BENCHMARK_COMPANIES[:12]):
        out.append(
            ExamSpec(
                exam_id=f"acs_l12_{i+1:03d}",
                level=12,
                analyst="committee",
                question=(
                    f"Prediction accuracy for {co['name']}: track historical opinion → outcome → "
                    f"correct/wrong → lessons → analyst accuracy."
                ),
                company=co["name"],
                ticker=co["ticker"],
                topic="Prediction Accuracy",
                must_include=["opinion", "outcome", "correct", "wrong", "lesson", "accuracy"],
                tags=["prediction_accuracy"],
            )
        )
    return out


def level15_exams() -> list[ExamSpec]:
    stresses = [
        "Missing financials",
        "Conflicting evidence",
        "Incomplete valuation",
        "Weak macro",
        "Contradictory broker reports",
        "Low confidence",
        "Noisy data",
    ]
    out = []
    for i, s in enumerate(stresses):
        co = BENCHMARK_COMPANIES[i % len(BENCHMARK_COMPANIES)]
        out.append(
            ExamSpec(
                exam_id=f"acs_l15_{i+1:03d}",
                level=15,
                analyst="risk",
                question=f"Stress test on {co['name']}: {s}. Show graceful degradation — lower confidence, state gaps, do not invent certainty.",
                company=co["name"],
                ticker=co["ticker"],
                topic=s,
                must_include=["degrade", "confidence", "gap"],
                tags=["stress_tests"],
            )
        )
    return out


def level16_exams() -> list[ExamSpec]:
    out = []
    for i, co in enumerate(BENCHMARK_COMPANIES):
        out.append(
            ExamSpec(
                exam_id=f"acs_l16_{i+1:03d}",
                level=16,
                analyst="committee",
                question=f"Benchmark suite: produce a mini institutional brief on {co['name']} ({co['sector']}).",
                company=co["name"],
                ticker=co["ticker"],
                topic="Benchmark",
                must_include=[co["name"].split()[0].lower(), "business", "risk", "conclusion"],
                tags=["benchmark_suite", co["sector"].lower().replace(" ", "_")],
            )
        )
    return out


def level17_exams() -> list[ExamSpec]:
    out = []
    for i, c in enumerate(CONCEPTS):
        out.append(
            ExamSpec(
                exam_id=f"acs_l17_{i+1:03d}",
                level=17,
                analyst="general",
                question=(
                    f"Knowledge coverage for {c}: report Coverage, Confidence, Books, Frameworks, "
                    f"Cases, Decision Rules, Examples, Counter Examples, Analysts Using It."
                ),
                topic=c,
                must_include=["coverage", "confidence", "framework", "case", "decision", "example"],
                tags=["knowledge_coverage"],
            )
        )
    return out


def shared_exams() -> list[ExamSpec]:
    return (
        level1_exams()
        + level2_exams()
        + level3_exams()
        + level4_exams()
        + level5_exams()
        + level7_exams()
        + level9_exams()
        + level10_exams()
        + level12_exams()
        + level15_exams()
        + level16_exams()
        + level17_exams()
    )
