"""Validation Suite exam catalog — Levels 1–8."""

from __future__ import annotations

from academy.validation_suite.schema import ExamItem


def all_exams() -> list[ExamItem]:
    return [
        *_level1_concept_recall(),
        *_level2_framework_application(),
        *_level3_cross_book_synthesis(),
        *_level4_case_transfer(),
        *_level5_counter_examples(),
        *_level6_analyst_specific(),
        *_level7_memory(),
        *_level8_decision(),
    ]


def exams_for_level(level: int) -> list[ExamItem]:
    return [e for e in all_exams() if e.level == level]


def exam_by_id(exam_id: str) -> ExamItem | None:
    for e in all_exams():
        if e.exam_id == exam_id:
            return e
    return None


def _level1_concept_recall() -> list[ExamItem]:
    common = [
        "Defines the concept correctly",
        "Explains why it matters",
        "Describes when to apply it",
        "Describes when not to apply it",
        "Does not quote books",
    ]
    items = [
        ("l1_roic", "What is ROIC?", ["roic", "invested capital", "nopat", "cost of capital"]),
        ("l1_roic_vs_roe", "Why is ROIC more important than ROE in many businesses?", ["roic", "roe", "leverage", "operations"]),
        ("l1_mos", "Explain Margin of Safety.", ["margin of safety", "intrinsic", "cushion", "uncertainty"]),
        ("l1_capital_cycle", "What is the Capital Cycle?", ["capital cycle", "capacity", "returns", "supply"]),
        ("l1_network", "What is a Network Effect?", ["network", "users", "value", "scale"]),
        ("l1_switching", "Explain Switching Costs.", ["switching", "retention", "friction", "customer"]),
        ("l1_economic_profit", "What is Economic Profit?", ["economic profit", "roic", "wacc", "spread"]),
        ("l1_reverse_dcf", "Explain Reverse DCF.", ["reverse", "implied", "expectations", "growth"]),
        ("l1_earnings_quality", "What is Earnings Quality?", ["earnings quality", "cash", "accrual", "sustainable"]),
        ("l1_ccc", "Explain Cash Conversion Cycle.", ["cash conversion", "inventory", "receivable", "payable"]),
    ]
    out = []
    for eid, q, must in items:
        out.append(
            ExamItem(
                exam_id=eid,
                level=1,
                question=q,
                analyst="general",
                must_include=must,
                must_not_include=["according to the book", "on page", "chapter ", ".pdf"],
                pass_criteria=common,
                tags=["concept_recall"],
            )
        )
    return out


def _level2_framework_application() -> list[ExamItem]:
    common = [
        "Applies the framework correctly",
        "Uses company-specific evidence",
        "Produces a conclusion",
        "Does not merely define the framework",
    ]
    return [
        ExamItem(
            exam_id="l2_hdfc_porter",
            level=2,
            question="Analyse HDFC Bank using Porter's Five Forces.",
            analyst="business",
            company="HDFC Bank",
            ticker="HDFCBANK",
            framework="porter",
            must_include=["rivalry", "buyer", "supplier", "substitute", "entrant", "conclusion"],
            pass_criteria=common,
            tags=["porter", "banking"],
        ),
        ExamItem(
            exam_id="l2_ultratech_capital_cycle",
            level=2,
            question="Apply the Capital Cycle to UltraTech Cement.",
            analyst="business",
            company="UltraTech Cement",
            ticker="ULTRACEMCO",
            framework="capital_cycle",
            must_include=["capacity", "returns", "cycle", "conclusion"],
            pass_criteria=common,
            tags=["capital_cycle", "cement"],
        ),
        ExamItem(
            exam_id="l2_nestle_mos",
            level=2,
            question="Apply Margin of Safety to Nestlé India.",
            analyst="valuation",
            company="Nestlé India",
            ticker="NESTLEIND",
            framework="margin_of_safety",
            must_include=["intrinsic", "cushion", "uncertainty", "conclusion"],
            pass_criteria=common,
            tags=["mos", "fmcg"],
        ),
        ExamItem(
            exam_id="l2_eternal_narrative",
            level=2,
            question="Apply Narrative and Numbers to Eternal.",
            analyst="valuation",
            company="Eternal",
            ticker="ETERNAL",
            framework="narrative_numbers",
            must_include=["narrative", "number", "evidence", "conclusion"],
            pass_criteria=common,
            tags=["narrative", "consumer_internet"],
        ),
        ExamItem(
            exam_id="l2_tcs_roic",
            level=2,
            question="Apply ROIC analysis to TCS.",
            analyst="financial",
            company="TCS",
            ticker="TCS",
            framework="roic",
            must_include=["roic", "cash", "reinvestment", "conclusion"],
            pass_criteria=common,
            tags=["roic", "it_services"],
        ),
    ]


def _level3_cross_book_synthesis() -> list[ExamItem]:
    return [
        ExamItem(
            exam_id="l3_hdfc_premium",
            level=3,
            question=(
                "Explain whether HDFC Bank deserves a premium valuation using "
                "Damodaran, Graham and Fisher."
            ),
            analyst="valuation",
            company="HDFC Bank",
            ticker="HDFCBANK",
            authors=["Damodaran", "Graham", "Fisher"],
            must_include=["fisher", "damodaran", "graham", "business quality", "intrinsic", "margin of safety", "institutional"],
            pass_criteria=[
                "Integrates multiple authors naturally",
                "Does not answer from only one book",
                "Produces a unified institutional view",
            ],
            tags=["synthesis", "banking"],
        ),
        ExamItem(
            exam_id="l3_roic_multi_author",
            level=3,
            question="How should I interpret high ROIC across Damodaran, Graham, Klarman, Fridson and Fisher?",
            analyst="valuation",
            authors=["Damodaran", "Graham", "Klarman", "Fridson", "Fisher"],
            must_include=["damodaran", "graham", "klarman", "cash", "margin of safety"],
            pass_criteria=[
                "Integrates multiple authors naturally",
                "Does not answer from only one book",
                "Produces a unified institutional view",
            ],
            tags=["synthesis", "roic"],
        ),
    ]


def _level4_case_transfer() -> list[ExamItem]:
    common = [
        "Identifies the right analogue",
        "Explains similarities and differences",
        "Draws transferable lessons",
    ]
    return [
        ExamItem(
            exam_id="l4_eternal_amazon_groupon",
            level=4,
            question="Does Eternal resemble Amazon or Groupon? Explain why.",
            analyst="business",
            company="Eternal",
            ticker="ETERNAL",
            analogues=["Amazon", "Groupon"],
            must_include=["amazon", "groupon", "similar", "differ", "lesson"],
            pass_criteria=common,
            tags=["case_transfer"],
        ),
        ExamItem(
            exam_id="l4_apple_cocacola",
            level=4,
            question="Does Apple resemble Coca-Cola in pricing power?",
            analyst="business",
            company="Apple",
            ticker="AAPL",
            analogues=["Coca-Cola"],
            must_include=["pricing", "brand", "similar", "differ", "lesson"],
            pass_criteria=common,
            tags=["case_transfer"],
        ),
        ExamItem(
            exam_id="l4_yesbank_wirecard",
            level=4,
            question="Is Yes Bank more like Wirecard or a cyclical turnaround?",
            analyst="risk",
            company="Yes Bank",
            ticker="YESBANK",
            analogues=["Wirecard", "cyclical turnaround"],
            must_include=["wirecard", "turnaround", "similar", "differ", "lesson"],
            pass_criteria=common,
            tags=["case_transfer", "failure"],
        ),
        ExamItem(
            exam_id="l4_reliance_allocation",
            level=4,
            question="Is Reliance closer to Berkshire or General Electric in capital allocation?",
            analyst="management",
            company="Reliance",
            ticker="RELIANCE",
            analogues=["Berkshire", "General Electric"],
            must_include=["berkshire", "general electric", "capital", "similar", "differ", "lesson"],
            pass_criteria=common,
            tags=["case_transfer", "capital_allocation"],
        ),
    ]


def _level5_counter_examples() -> list[ExamItem]:
    return [
        ExamItem(
            exam_id="l5_high_roe_misleading",
            level=5,
            question="When does a high ROE become misleading?",
            analyst="financial",
            must_include=["leverage", "buyback", "one-off", "accounting"],
            pass_criteria=[
                "Identifies exceptions",
                "Does not treat concepts as universally true",
            ],
            tags=["counter_example", "roe"],
        ),
        ExamItem(
            exam_id="l5_high_roic_misleading",
            level=5,
            question="When does a high ROIC become misleading?",
            analyst="financial",
            must_include=["peak", "cash", "accounting", "cycle"],
            pass_criteria=[
                "Identifies exceptions",
                "Does not treat concepts as universally true",
            ],
            tags=["counter_example", "roic"],
        ),
        ExamItem(
            exam_id="l5_low_multiple_trap",
            level=5,
            question="When is a low valuation multiple a value trap rather than a bargain?",
            analyst="valuation",
            must_include=["structural", "roic", "catalyst", "trap"],
            pass_criteria=[
                "Identifies exceptions",
                "Does not treat concepts as universally true",
            ],
            tags=["counter_example", "value_trap"],
        ),
    ]


def _level6_analyst_specific() -> list[ExamItem]:
    return [
        # Business
        ExamItem(
            exam_id="l6_ba_apple_moat",
            level=6,
            question="Explain Apple's moat.",
            analyst="business",
            company="Apple",
            ticker="AAPL",
            must_include=["ecosystem", "switching", "pricing", "services"],
            pass_criteria=["Stays in business domain", "Uses company evidence", "Reaches a reasoned view"],
            tags=["business"],
        ),
        ExamItem(
            exam_id="l6_ba_nestle_pricing",
            level=6,
            question="Why is Nestlé's pricing power durable?",
            analyst="business",
            company="Nestlé India",
            ticker="NESTLEIND",
            must_include=["brand", "distribution", "pricing", "retention"],
            pass_criteria=["Stays in business domain", "Uses company evidence", "Reaches a reasoned view"],
            tags=["business"],
        ),
        ExamItem(
            exam_id="l6_ba_nokia",
            level=6,
            question="Why did Nokia lose its competitive advantage?",
            analyst="business",
            company="Nokia",
            must_include=["disruption", "ecosystem", "innovation", "moat"],
            pass_criteria=["Stays in business domain", "Uses company evidence", "Reaches a reasoned view"],
            tags=["business"],
        ),
        ExamItem(
            exam_id="l6_ba_costco",
            level=6,
            question="Why is Costco's membership model powerful?",
            analyst="business",
            company="Costco",
            must_include=["membership", "retention", "scale", "customer"],
            pass_criteria=["Stays in business domain", "Uses company evidence", "Reaches a reasoned view"],
            tags=["business"],
        ),
        # Financial
        ExamItem(
            exam_id="l6_fa_cash_vs_earnings",
            level=6,
            question="Does cash flow support reported earnings?",
            analyst="financial",
            company="TCS",
            ticker="TCS",
            must_include=["cash", "earnings", "conversion"],
            pass_criteria=["Stays in financial domain", "Uses evidence", "Reaches a reasoned view"],
            tags=["financial"],
        ),
        ExamItem(
            exam_id="l6_fa_wc",
            level=6,
            question="Is working capital improving?",
            analyst="financial",
            company="Nestlé India",
            ticker="NESTLEIND",
            must_include=["working capital", "inventory", "receivable"],
            pass_criteria=["Stays in financial domain", "Uses evidence", "Reaches a reasoned view"],
            tags=["financial"],
        ),
        ExamItem(
            exam_id="l6_fa_growth_fcf",
            level=6,
            question="Is growth backed by free cash flow?",
            analyst="financial",
            company="TCS",
            ticker="TCS",
            must_include=["growth", "free cash", "reinvestment"],
            pass_criteria=["Stays in financial domain", "Uses evidence", "Reaches a reasoned view"],
            tags=["financial"],
        ),
        ExamItem(
            exam_id="l6_fa_margins",
            level=6,
            question="Are margins structurally improving?",
            analyst="financial",
            company="HDFC Bank",
            ticker="HDFCBANK",
            must_include=["margin", "structural", "cycle"],
            pass_criteria=["Stays in financial domain", "Uses evidence", "Reaches a reasoned view"],
            tags=["financial"],
        ),
        # Valuation
        ExamItem(
            exam_id="l6_va_pe_assumptions",
            level=6,
            question="What assumptions justify today's PE?",
            analyst="valuation",
            company="Nestlé India",
            ticker="NESTLEIND",
            must_include=["growth", "return", "risk", "expectation"],
            pass_criteria=["Stays in valuation domain", "Debates expectations", "No cheap/expensive slogan alone"],
            tags=["valuation"],
        ),
        ExamItem(
            exam_id="l6_va_growth_priced",
            level=6,
            question="What growth is priced into the stock?",
            analyst="valuation",
            company="TCS",
            ticker="TCS",
            must_include=["implied", "growth", "reverse"],
            pass_criteria=["Stays in valuation domain", "Debates expectations", "No cheap/expensive slogan alone"],
            tags=["valuation"],
        ),
        ExamItem(
            exam_id="l6_va_mos",
            level=6,
            question="Is the margin of safety adequate?",
            analyst="valuation",
            company="HDFC Bank",
            ticker="HDFCBANK",
            must_include=["margin of safety", "uncertainty", "intrinsic"],
            pass_criteria=["Stays in valuation domain", "Debates expectations", "No cheap/expensive slogan alone"],
            tags=["valuation"],
        ),
        ExamItem(
            exam_id="l6_va_change_opinion",
            level=6,
            question="What would change your valuation opinion?",
            analyst="valuation",
            company="HDFC Bank",
            ticker="HDFCBANK",
            must_include=["assumption", "growth", "return", "risk"],
            pass_criteria=["Stays in valuation domain", "Debates expectations", "No cheap/expensive slogan alone"],
            tags=["valuation"],
        ),
    ]


def _level7_memory() -> list[ExamItem]:
    return [
        ExamItem(
            exam_id="l7_hdfc_what_changed",
            level=7,
            question="What changed in HDFC Bank since the last review?",
            analyst="business",
            company="HDFC Bank",
            ticker="HDFCBANK",
            must_include=["loan", "deposit", "nim", "capital", "previous", "updated"],
            pass_criteria=[
                "References prior review memory",
                "Tracks key operating metrics",
                "States previous and updated opinion",
            ],
            tags=["memory"],
        ),
    ]


def _level8_decision() -> list[ExamItem]:
    return [
        ExamItem(
            exam_id="l8_invest_hdfc",
            level=8,
            question="Should I invest in HDFC Bank?",
            analyst="committee",
            company="HDFC Bank",
            ticker="HDFCBANK",
            must_include=["business", "financial", "valuation", "risk", "committee", "conclusion"],
            must_not_include=[],
            pass_criteria=[
                "Builds Business → Financials → Valuation → Risks → Committee chain",
                "Does not answer with bare yes/no",
                "Every major statement is justified",
            ],
            tags=["decision"],
        ),
    ]
