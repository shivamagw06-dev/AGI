"""Curated institutional seed — AGI-owned knowledge objects (not book copies).

Provides permanent intellectual foundation covering valuation, accounting,
corporate finance, investment methodologies and sector academies.
Attributed as curriculum seed with chapter references, never verbatim text.
"""

from __future__ import annotations

from academy.books.schema import BookConcept, BookMeta, ChapterNode, FormulaObject, FrameworkObject


def seed_books() -> list[BookMeta]:
    return [
        BookMeta(
            book_id="seed_valuation_guide",
            title="AGI Institutional Valuation Guide",
            authors=["AGI Academy Curriculum"],
            subject="Valuation",
            topics=["DCF", "multiples", "WACC", "terminal value"],
            difficulty="advanced",
            source_format="seed",
            academies=["valuation", "corporate_finance"],
        ),
        BookMeta(
            book_id="seed_accounting_ref",
            title="AGI Investor Accounting Reference",
            authors=["AGI Academy Curriculum"],
            subject="Accounting",
            topics=["earnings quality", "accruals", "cash conversion"],
            difficulty="intermediate",
            source_format="seed",
            academies=["accounting"],
        ),
        BookMeta(
            book_id="seed_investment_frameworks",
            title="AGI Investment Frameworks Handbook",
            authors=["AGI Academy Curriculum"],
            subject="Investment",
            topics=["moat", "margin of safety", "quality", "capital allocation"],
            difficulty="intermediate",
            source_format="seed",
            academies=["investment", "sector_fmcg", "sector_banking", "sector_it_services"],
        ),
        BookMeta(
            book_id="seed_macro_econ",
            title="AGI Macro & Economics Primer",
            authors=["AGI Academy Curriculum"],
            subject="Economics",
            topics=["cycles", "rates", "inflation", "policy"],
            difficulty="intro",
            source_format="seed",
            academies=["economics", "macro"],
        ),
    ]


def seed_chapters() -> list[ChapterNode]:
    return [
        ChapterNode("seed_valuation_guide:ch1", "seed_valuation_guide", "Discounted Cash Flow", "chapter", 1, summary="Value equals expected cash flows discounted for risk and time."),
        ChapterNode("seed_valuation_guide:ch2", "seed_valuation_guide", "Cost of Capital", "chapter", 2, summary="Separate operating returns from financing costs."),
        ChapterNode("seed_valuation_guide:ch3", "seed_valuation_guide", "Relative Valuation", "chapter", 3, summary="Multiples require matched growth, risk and reinvestment."),
        ChapterNode("seed_accounting_ref:ch1", "seed_accounting_ref", "Accrual vs Cash", "chapter", 1, summary="Earnings quality hinges on cash conversion and accrual persistence."),
        ChapterNode("seed_accounting_ref:ch2", "seed_accounting_ref", "Balance Sheet Integrity", "chapter", 2, summary="Assets and liabilities encode capital intensity and leverage risk."),
        ChapterNode("seed_investment_frameworks:ch1", "seed_investment_frameworks", "Economic Moat", "chapter", 1, summary="Durable advantage shows up as ROIC above WACC for long periods."),
        ChapterNode("seed_investment_frameworks:ch2", "seed_investment_frameworks", "Capital Allocation", "chapter", 2, summary="Reinvestment, payout and M&A decide compounding."),
        ChapterNode("seed_investment_frameworks:ch3", "seed_investment_frameworks", "Consumer Staples Lens", "chapter", 3, summary="Brand power, pricing power and working capital define staples quality."),
        ChapterNode("seed_macro_econ:ch1", "seed_macro_econ", "Policy Transmission", "chapter", 1, summary="Rates and liquidity transmit into earnings and multiples."),
    ]


def seed_formulas() -> list[FormulaObject]:
    return [
        FormulaObject("seed_f_wacc", "WACC", "E/V*r_e + D/V*r_d*(1-t)", "Blended required return on the firm’s capital.", {"E": "equity value", "D": "debt value", "V": "E+D", "r_e": "cost of equity", "r_d": "cost of debt", "t": "tax rate"}, ["DCF discount rate", "EVA spread"], "valuation", "seed_valuation_guide", "Cost of Capital", 0.92),
        FormulaObject("seed_f_capm", "CAPM", "r_f + beta*(ERP)", "Equilibrium expected equity return for systematic risk.", {"r_f": "risk-free rate", "beta": "market beta", "ERP": "equity risk premium"}, ["cost of equity"], "valuation", "seed_valuation_guide", "Cost of Capital", 0.9),
        FormulaObject("seed_f_roic", "ROIC", "NOPAT / Invested Capital", "Return earned on capital used in operations.", {"NOPAT": "after-tax operating profit", "Invested Capital": "operating assets − operating liabilities"}, ["moat test", "value creation"], "corporate_finance", "seed_investment_frameworks", "Economic Moat", 0.93),
        FormulaObject("seed_f_roe", "ROE", "Net Income / Equity", "Return on owners’ book equity; distorted by leverage.", {"Net Income": "bottom-line earnings", "Equity": "book equity"}, ["bank profitability", "leverage check"], "accounting", "seed_accounting_ref", "Balance Sheet Integrity", 0.9),
        FormulaObject("seed_f_roce", "ROCE", "EBIT / Capital Employed", "Pre-tax operating return on capital employed.", {"EBIT": "operating profit", "Capital Employed": "equity + debt"}, ["industrial peer compare"], "corporate_finance", "seed_investment_frameworks", "Capital Allocation", 0.88),
        FormulaObject("seed_f_fcf", "Free Cash Flow", "CFO − Capex", "Cash available after maintaining/growing the asset base.", {"CFO": "operating cash flow", "Capex": "capital expenditure"}, ["DCF numerator", "dividend capacity"], "valuation", "seed_valuation_guide", "Discounted Cash Flow", 0.92),
        FormulaObject("seed_f_tv", "Terminal Value", "FCF_(n+1) / (r − g)", "Continuing value under stable growth.", {"FCF_(n+1)": "first steady-state FCF", "r": "discount rate", "g": "perpetual growth"}, ["DCF terminal"], "valuation", "seed_valuation_guide", "Discounted Cash Flow", 0.9),
        FormulaObject("seed_f_iv", "Intrinsic Value", "Σ CF_t/(1+r)^t + TV/(1+r)^n", "Present value of expected owner cash flows.", {"CF_t": "cash flow", "r": "discount rate", "TV": "terminal value"}, ["absolute valuation"], "valuation", "seed_valuation_guide", "Discounted Cash Flow", 0.91),
    ]


def seed_frameworks() -> list[FrameworkObject]:
    return [
        FrameworkObject(
            "seed_fw_moat", "Economic Moat", "Test whether excess returns can persist.",
            ["ROIC history", "pricing power", "switching costs", "scale", "intangibles"],
            ["moat width", "duration estimate", "fade assumptions"],
            ["If ROIC > WACC with durable drivers, allow longer competitive advantage period", "Fade returns when advantages erode"],
            ["quality investing", "DCF competitive advantage period"],
            "investment", ["roic", "competitive_advantage"], "seed_investment_frameworks", "Economic Moat", 0.93,
        ),
        FrameworkObject(
            "seed_fw_mos", "Margin of Safety", "Require a buffer between price and value.",
            ["intrinsic value", "uncertainty", "balance sheet risk"],
            ["entry discipline", "downside protection"],
            ["Buy only when market price is sufficiently below conservative value"],
            ["value investing"],
            "investment", ["intrinsic_value"], "seed_investment_frameworks", "Economic Moat", 0.9,
        ),
        FrameworkObject(
            "seed_fw_alloc", "Capital Allocation", "Judge how management deploys cash.",
            ["reinvestment opportunities", "ROIC vs WACC", "leverage", "buybacks", "M&A"],
            ["compounding path", "per-share value impact"],
            ["Prefer high-ROIC reinvestment; return cash when opportunities are scarce; punish value-destructive M&A"],
            ["corporate finance", "owner earnings"],
            "corporate_finance", ["roic", "roe"], "seed_investment_frameworks", "Capital Allocation", 0.94,
        ),
        FrameworkObject(
            "seed_fw_five_forces", "Porter's Five Forces", "Map industry profit pressure.",
            ["rivalry", "new entrants", "substitutes", "buyer power", "supplier power"],
            ["industry attractiveness", "margin sustainability"],
            ["High force intensity compresses long-run ROIC"],
            ["sector analysis"],
            "investment", ["competitive_advantage"], "seed_investment_frameworks", "Economic Moat", 0.88,
        ),
        FrameworkObject(
            "seed_fw_swot", "SWOT", "Organise internal and external factors.",
            ["strengths", "weaknesses", "opportunities", "threats"],
            ["issue tree", "research outline"],
            ["Separate facts from narratives; link each factor to cash flows or risk"],
            ["research writing"],
            "investment", [], "seed_investment_frameworks", "Capital Allocation", 0.8,
        ),
        FrameworkObject(
            "seed_fw_lifecycle", "Business Life Cycle", "Match metrics and valuation to stage.",
            ["growth", "margins", "reinvestment", "cash conversion"],
            ["stage label", "appropriate KPIs"],
            ["Early stage: growth/reinvestment; mature: FCF/payout; decline: capital release"],
            ["forecasting", "multiples selection"],
            "investment", [], "seed_investment_frameworks", "Capital Allocation", 0.86,
        ),
        FrameworkObject(
            "seed_fw_staples", "Consumer Staples Quality", "Assess brand and pricing durability for staples.",
            ["brand power", "pricing power", "distribution", "working capital", "ROIC"],
            ["quality score", "moat evidence"],
            ["Sustainable pricing power with high ROIC and disciplined working capital supports premium multiples only with growth"],
            ["FMCG / Nestlé-class analysis"],
            "sector_fmcg", ["brand_power", "pricing_power", "working_capital", "roic", "economic_moat"],
            "seed_investment_frameworks", "Consumer Staples Lens", 0.92,
        ),
    ]


def seed_concepts() -> list[BookConcept]:
    return [
        BookConcept("seed_c_intrinsic_value", "Intrinsic Value", "Estimated worth based on expected cash flows and risk, independent of market price.", "Use as an anchor; never confuse price with value.", ["Compare market price to conservative intrinsic value"], ["margin_of_safety", "dcf"], ["seed_f_iv"], ["seed_fw_mos"], [], ["All"], "valuation", "advanced", 0.93, "seed_valuation_guide", "Discounted Cash Flow"),
        BookConcept("seed_c_wacc", "WACC", "Weighted average cost of capital — the blended hurdle rate for firm cash flows.", "Must be consistent with cash-flow claims (firm vs equity).", [], ["capm", "roic"], ["seed_f_wacc", "seed_f_capm"], ["seed_fw_alloc"], [], ["All"], "valuation", "advanced", 0.92, "seed_valuation_guide", "Cost of Capital"),
        BookConcept("seed_c_roic", "ROIC", "Return on invested capital earned by the operating business.", "Compare to WACC to judge value creation.", [], ["economic_moat", "capital_allocation"], ["seed_f_roic"], ["seed_fw_moat", "seed_fw_alloc"], [], ["All"], "corporate_finance", "intermediate", 0.94, "seed_investment_frameworks", "Economic Moat"),
        BookConcept("seed_c_roe", "ROE", "Return on equity; rises with leverage even when operating returns do not.", "Always read beside leverage and ROIC.", [], ["capital_allocation"], ["seed_f_roe"], ["seed_fw_alloc"], ["HDFCBANK"], ["Banks"], "accounting", "intermediate", 0.9, "seed_accounting_ref", "Balance Sheet Integrity"),
        BookConcept("seed_c_fcf", "Free Cash Flow", "Cash generated after reinvestment needed to sustain the business.", "Primary input to owner-oriented valuation.", [], ["intrinsic_value"], ["seed_f_fcf"], [], [], ["All"], "valuation", "intermediate", 0.93, "seed_valuation_guide", "Discounted Cash Flow"),
        BookConcept("seed_c_moat", "Economic Moat", "Structural advantage that protects ROIC above the cost of capital.", "Evidence beats slogans — look for persistence and drivers.", ["Switching costs", "intangible brand", "cost scale"], ["roic", "competitive_advantage"], ["seed_f_roic"], ["seed_fw_moat"], ["NESTLEIND", "ASIANPAINT"], ["FMCG"], "investment", "intermediate", 0.94, "seed_investment_frameworks", "Economic Moat"),
        BookConcept("seed_c_mos", "Margin of Safety", "Gap between conservative intrinsic value and market price that absorbs error.", "Wider uncertainty demands a wider gap.", [], ["intrinsic_value"], ["seed_f_iv"], ["seed_fw_mos"], [], ["All"], "investment", "intermediate", 0.91, "seed_investment_frameworks", "Economic Moat"),
        BookConcept("seed_c_alloc", "Capital Allocation", "Management choices on reinvestment, payout, leverage and M&A.", "The bridge from ROIC to per-share compounding.", [], ["roic", "roe"], ["seed_f_roic"], ["seed_fw_alloc"], [], ["All"], "corporate_finance", "advanced", 0.94, "seed_investment_frameworks", "Capital Allocation"),
        BookConcept("seed_c_brand", "Brand Power", "Ability of a brand to sustain preference and protect volumes.", "Relevant for staples and discretionary franchises.", [], ["pricing_power", "economic_moat"], [], ["seed_fw_staples"], ["NESTLEIND"], ["FMCG"], "sector_fmcg", "intermediate", 0.9, "seed_investment_frameworks", "Consumer Staples Lens"),
        BookConcept("seed_c_pricing", "Pricing Power", "Ability to raise prices without losing unit demand disproportionately.", "Visible in margin resilience through cost shocks.", [], ["brand_power", "roic"], [], ["seed_fw_staples"], ["NESTLEIND"], ["FMCG"], "sector_fmcg", "intermediate", 0.9, "seed_investment_frameworks", "Consumer Staples Lens"),
        BookConcept("seed_c_wc", "Working Capital", "Operating liquidity tied in inventory, receivables and payables.", "Staples with negative or tight WC improve cash conversion.", [], ["fcf", "roic", "cash_conversion"], ["seed_f_fcf"], ["seed_fw_staples"], ["NESTLEIND"], ["FMCG"], "sector_fmcg", "intermediate", 0.88, "seed_investment_frameworks", "Consumer Staples Lens"),
        BookConcept("seed_c_cash_conversion", "Cash Conversion", "How reliably accounting profits become free cash flow.", "Critical bridge from earnings quality to owner returns.", [], ["working_capital", "fcf", "earnings_quality"], ["seed_f_fcf"], ["seed_fw_staples"], ["NESTLEIND"], ["FMCG"], "sector_fmcg", "intermediate", 0.9, "seed_investment_frameworks", "Consumer Staples Lens"),
        BookConcept("seed_c_premium_valuation", "Premium Valuation", "Market multiple above peers justified only by durable ROIC, growth and cash conversion.", "Premium without economic advantage is fragile.", [], ["economic_moat", "roic", "pricing_power"], [], ["seed_fw_staples", "seed_fw_moat"], ["NESTLEIND"], ["FMCG"], "valuation", "advanced", 0.9, "seed_investment_frameworks", "Consumer Staples Lens"),
        BookConcept("seed_c_comp_adv", "Competitive Advantage", "Position that enables returns above opportunity cost of capital.", "Must be observable in economics, not only narrative.", [], ["economic_moat", "valuation"], [], ["seed_fw_moat", "seed_fw_five_forces"], [], ["All"], "investment", "intermediate", 0.9, "seed_investment_frameworks", "Economic Moat"),
        BookConcept("seed_c_value", "Value Investing", "Seek securities priced below conservative intrinsic value.", "Requires independent valuation and patience.", [], ["margin_of_safety"], [], ["seed_fw_mos"], [], ["All"], "investment", "intro", 0.88, "seed_investment_frameworks", "Economic Moat"),
        BookConcept("seed_c_quality", "Quality Investing", "Prefer businesses with durable ROIC, clean accounting and disciplined allocation.", "Quality is an economic trait, not a style label alone.", [], ["roic", "economic_moat"], [], ["seed_fw_moat", "seed_fw_alloc"], [], ["All"], "investment", "intermediate", 0.9, "seed_investment_frameworks", "Capital Allocation"),
        BookConcept("seed_c_growth", "Growth Investing", "Pay for future cash-flow expansion when reinvestment earns above WACC.", "Growth without returns destroys value.", [], ["roic", "wacc"], [], ["seed_fw_lifecycle"], [], ["All"], "investment", "intermediate", 0.87, "seed_investment_frameworks", "Capital Allocation"),
        BookConcept("seed_c_accruals", "Accrual Accounting", "Earnings recognise economic events before or after cash moves.", "High accruals require cash-conversion scrutiny.", [], ["fcf"], [], [], [], ["All"], "accounting", "intermediate", 0.89, "seed_accounting_ref", "Accrual vs Cash"),
        BookConcept("seed_c_earnings_quality", "Earnings Quality", "Degree to which reported earnings map to sustainable cash generation.", "Adjust for one-offs, capitalisation choices and working-capital swings.", [], ["accrual_accounting", "fcf"], [], [], [], ["All"], "accounting", "advanced", 0.9, "seed_accounting_ref", "Accrual vs Cash"),
        BookConcept("seed_c_policy", "Policy Transmission", "How monetary and fiscal actions affect activity, rates and asset prices.", "Links macro regime to earnings and discount rates.", [], [], [], [], [], ["Banks", "Real Estate"], "macro", "intro", 0.86, "seed_macro_econ", "Policy Transmission"),
        BookConcept("seed_c_nim", "Net Interest Margin", "Core bank spread between asset yields and funding costs.", "Sensitive to rate cycles and liability mix.", [], ["roe"], ["seed_f_roe"], [], ["HDFCBANK"], ["Banks"], "sector_banking", "intermediate", 0.88, "seed_investment_frameworks", "Capital Allocation"),
        BookConcept("seed_c_utilisation", "Utilisation", "Billable deployment of IT services capacity.", "With pricing and deal wins, drives near-term margin.", [], [], [], [], ["INFY", "TCS"], ["IT"], "sector_it_services", "intermediate", 0.85, "seed_investment_frameworks", "Capital Allocation"),
    ]


def all_seed_concepts() -> list[BookConcept]:
    concepts = seed_concepts()
    for c in concepts:
        # normalise related ids to concept_ids where obvious
        remap = {
            "margin_of_safety": "seed_c_mos",
            "dcf": "seed_c_fcf",
            "capm": "seed_c_wacc",
            "roic": "seed_c_roic",
            "economic_moat": "seed_c_moat",
            "capital_allocation": "seed_c_alloc",
            "competitive_advantage": "seed_c_comp_adv",
            "intrinsic_value": "seed_c_intrinsic_value",
            "brand_power": "seed_c_brand",
            "pricing_power": "seed_c_pricing",
            "working_capital": "seed_c_wc",
            "cash_conversion": "seed_c_cash_conversion",
            "fcf": "seed_c_fcf",
            "roe": "seed_c_roe",
            "wacc": "seed_c_wacc",
            "accrual_accounting": "seed_c_accruals",
            "earnings_quality": "seed_c_earnings_quality",
            "pricing_power": "seed_c_pricing",
            "valuation": "seed_c_premium_valuation",
        }
        c.related_concepts = [remap.get(r, r) for r in c.related_concepts]
    return concepts
