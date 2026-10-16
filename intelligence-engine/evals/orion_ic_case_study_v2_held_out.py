"""Orion Global Industries — CFA-Level Institutional Case Study V2 (HELD OUT).

CRITICAL RULES
--------------
1. NEVER import this module into matchers, composers, gold patterns, adversarial,
   family_classifier, or ic_case_study detectors.
2. NEVER train on these questions.
3. Use only for evaluation / scorecards.
4. High score means integrated CFA-level IC reasoning on this set only —
   not unbounded proof of "genuine intelligence."

Designed so no single book solves it: accounting + valuation + macro + behavioural
+ credit + portfolio + evidence evaluation must be combined.
"""

from __future__ import annotations

from typing import Any

NEVER_TRAIN = True
EVALUATION_ONLY = True
CASE_ID = "orion_ic_case_v2"
CASE_TITLE = "Orion Global Industries — CFA-Level Institutional Case Study V2.0"
TOTAL_RUBRIC_POINTS = 500

CASE_FACTS = """
ORION RESEARCH DOSSIER V2 — fictional multinational for CFA-level institutional reasoning.
Company: Orion Global Industries. Mix: Industrial Automation 35%; Renewable Energy Equipment 25%;
AI Industrial Software 20%; Aerospace Components 20%. Operations in 40 countries; 6 reporting segments;
3 reporting currencies (USD, EUR, INR); 2 recent acquisitions (Nova Robotics FY25; GreenGrid FY26);
one planned spin-off of Aerospace Components announced but not completed.

FIVE-YEAR CONSOLIDATED (USD mn):
FY22 Rev 18,200 | EBITDA margin 19% | NI 1,420 | FCF 1,110 | ROIC 14% | Net debt 4,800
FY23 Rev 19,800 | EBITDA margin 20% | NI 1,610 | FCF 980 | ROIC 15% | Net debt 5,400
FY24 Rev 22,100 | EBITDA margin 18% | NI 1,740 | FCF 420 | ROIC 13% | Net debt 7,200
FY25 Rev 26,400 | EBITDA margin 17% | NI 2,050 | FCF -180 | ROIC 11% | Net debt 9,800
FY26 Rev 31,200 | EBITDA margin 15% | NI 2,480 | FCF -640 | ROIC 9% | Net debt 12,600
Reported NI FY26 includes USD 310m one-off disposal/FX gain and USD 90m capitalised software R&D previously expensed.
Auditor changed in FY25. Prior-year revenue restatement: FY24 revenue cut USD 220m (channel stuffing correction).

QUARTER LATEST: Rev +24% YoY; NI +31%; Op. margin 14%↓; FCF -USD 210m; Receivables +48%; Inventory +41%
(ageing: >180 days receivables up sharply); Deferred revenue flat despite software claim of “bookings boom”;
Lease liabilities +22%; Pension deficit widened; SBC expense +35%; Customer concentration top client 18%, top-5 46%.

BALANCE / CREDIT: Debt maturity wall — 38% of gross debt due within 24 months; Interest coverage 3.1×↓ from 6.2×;
Revolver 45% drawn; Bond yield spreads widened +140 bps; Rating agency placed on negative outlook (not downgraded);
Covenant headroom on net-debt/EBITDA thin (3.6× vs 4.0× cap).

GEO / FX / MACRO: EUR and INR reporting; USD strengthened; management cites “currency gains boosted reported profit”;
Oil +22%; Copper +18%; Policy rates up then partial cuts; Inflation sticky in key plants; Trade-policy risk on aerospace;
GDP soft in Europe; India mix rising.

SEGMENTS: Automation solid but WC heavy; Renewables revenue up, margins compressed by commodity inputs;
Software ARR narrative strong but deferred revenue and cash collection lag; Aerospace backlog healthy, spin-off planned.

VALUATION PACK (provided models): DCF USD 48/sh; Relative (peers) USD 39/sh; Residual income USD 41/sh;
Reverse DCF implies 16% FCF CAGR for 10 years vs current negative FCF. Spot USD 52; 52w high USD 71; hist PE 22× now 34×;
EV/EBITDA 18× vs peers 12×.

CAPITAL ALLOCATION: Dividend held flat while FCF negative; Buybacks USD 400m in FY25–26 funded partly by debt;
Nova Robotics acquisition: goodwill large, earn-outs pending; GreenGrid still integrating; Capex elevated.

ESG: ESG score improved; emissions intensity down; meanwhile leverage and pension deficit worsened.

GUIDANCE / CALLS: CEO — “best demand environment in a decade”; CFO — “working capital temporary”; IR — “software will
double bookings”; Earnings call emphasises AI narrative; Investor deck shows hockey-stick FCF.

ANALYSTS: Broker A BUY tgt 78; Broker B SELL tgt 34; Broker C HOLD tgt 50; Consensus “Overweight” — two reports are
>9 months old and predate the restatement. Credit desk note more cautious than equity desk.

NEWS / FILINGS: Reuters — major Middle East renewables award (no exchange filing yet). Social media — CFO resigning
(unconfirmed). Official 10-K/annual report and audit opinion filed; audit opinion unqualified but EOM paragraph on
going-concern uncertainties around refinancing. Press rumour of bid interest — unverified.

HIDDEN CONTRADICTIONS TO DETECT: Fake/unverified positive news; accounting restatement; one-off gain inflating NI;
profit↑ cash↓; ESG↑ leverage↑; revenue↑ margins↓; FX gains boosting profit; conflicting analysts; outdated brokers;
management optimism unsupported by filings/deferred revenue/cash.

RULES: No Buy/Sell/Hold as advice; no price-target recommendation; separate evidence quality; show uncertainty;
detect traps rather than accept narratives.
""".strip()

RUBRIC_AREAS: dict[str, int] = {
    "financial_statement_analysis": 40,
    "accounting_red_flags": 30,
    "corporate_finance": 35,
    "equity_valuation": 60,
    "credit_analysis": 30,
    "macroeconomic_analysis": 35,
    "behavioural_finance": 25,
    "evidence_hierarchy": 25,
    "competing_committees": 50,
    "devils_advocate": 40,
    "scenario_analysis": 40,
    "portfolio_decision": 30,
    "three_audiences": 30,
    "audited_only_challenge": 30,
}

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "O01",
        "section": "1",
        "areas": ["financial_statement_analysis"],
        "marks": 40,
        "mode_hint": "ic_fsa_pack",
        "question": (
            "Financial statement analysis: evaluate revenue quality, earnings quality, cash conversion, "
            "working capital, accruals, one-off items, capitalised expenses, and return metrics."
        ),
        "must_include": [
            "revenue quality",
            "earnings quality",
            "cash conversion",
            "working capital",
            "accrual",
            "one-off",
            "capitalis",
            "roic",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O02",
        "section": "2",
        "areas": ["accounting_red_flags"],
        "marks": 30,
        "mode_hint": "ic_accounting_red_flags",
        "question": (
            "Identify every potential accounting red flag / warning sign (receivables, inventory, goodwill, "
            "deferred revenue, capitalisation policy, lease treatment, restatement, one-offs). For each: "
            "evidence, alternative explanations, and confidence."
        ),
        "must_include": [
            "receivable",
            "inventory",
            "goodwill",
            "deferred revenue",
            "restatement",
            "alternative",
            "confidence",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O03",
        "section": "3",
        "areas": ["corporate_finance"],
        "marks": 35,
        "mode_hint": "ic_capital_allocation",
        "question": (
            "Corporate finance assessment: capital allocation, dividend policy, buybacks, acquisition quality, "
            "ROIC vs WACC / cost of capital, and whether management is creating value."
        ),
        "must_include": [
            "capital allocation",
            "dividend",
            "buyback",
            "acquisition",
            "roic",
            "wacc",
            "value",
        ],
        "must_not_include": ["buy now", "sell now"],
    },
    {
        "id": "O04",
        "section": "4",
        "areas": ["equity_valuation"],
        "marks": 25,
        "mode_hint": "ic_four_method_valuation",
        "question": (
            "Equity valuation using four methods: DCF, relative valuation, residual income, and reverse DCF. "
            "State what each method is saying given the pack."
        ),
        "must_include": ["dcf", "relative", "residual income", "reverse dcf"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O05",
        "section": "4",
        "areas": ["equity_valuation"],
        "marks": 20,
        "mode_hint": "ic_valuation_divergence",
        "question": "Why do DCF, relative valuation, residual income and reverse DCF differ? Which assumptions drive each result?",
        "must_include": ["differ", "assumption", "cash", "multiple"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O06",
        "section": "4",
        "areas": ["equity_valuation"],
        "marks": 15,
        "mode_hint": "ic_valuation_weight",
        "question": "Which valuation method deserves the highest weight here, and why?",
        "must_include": ["weight", "cash", "reverse"],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O07",
        "section": "5",
        "areas": ["credit_analysis"],
        "marks": 30,
        "mode_hint": "ic_credit_analysis",
        "question": (
            "Credit analysis: interest coverage, debt maturity, liquidity, refinancing risk, "
            "covenant pressure, and rating outlook."
        ),
        "must_include": [
            "interest coverage",
            "maturity",
            "liquidity",
            "refinanc",
            "covenant",
            "rating",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O08",
        "section": "6",
        "areas": ["macroeconomic_analysis"],
        "marks": 35,
        "mode_hint": "ic_macro_stress",
        "question": (
            "Macroeconomic stress-test: interest rates, inflation, currency, commodity prices, GDP, and trade policy. "
            "Explain transmission mechanisms to Orion."
        ),
        "must_include": [
            "interest",
            "inflation",
            "currency",
            "commodity",
            "gdp",
            "trade",
            "transmission",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O09",
        "section": "7",
        "areas": ["behavioural_finance"],
        "marks": 25,
        "mode_hint": "ic_behavioural_v2",
        "question": (
            "Behavioural finance: identify confirmation bias, anchoring, narrative fallacy, availability bias, "
            "overconfidence, and loss aversion — explain how each could distort the investment case."
        ),
        "must_include": [
            "confirmation",
            "anchoring",
            "narrative",
            "availability",
            "overconfidence",
            "loss aversion",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O10",
        "section": "8",
        "areas": ["evidence_hierarchy"],
        "marks": 25,
        "mode_hint": "ic_evidence_rank",
        "question": (
            "Evidence hierarchy: rank annual report, audit report, earnings call, investor presentation, "
            "Reuters, Bloomberg, social media, and broker research. Explain why."
        ),
        "must_include": [
            "audit",
            "annual report",
            "earnings call",
            "reuters",
            "social media",
            "broker",
            "rank",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O11",
        "section": "9",
        "areas": ["competing_committees"],
        "marks": 50,
        "mode_hint": "ic_competing_committees",
        "question": (
            "Competing investment committees: produce three independent views — Committee A growth investors, "
            "Committee B value investors, Committee C credit committee. Same evidence, different conclusions, explain why."
        ),
        "must_include": [
            "committee a",
            "committee b",
            "committee c",
            "growth",
            "value",
            "credit",
        ],
        "must_not_include": ["definitely buy", "definitely sell"],
    },
    {
        "id": "O12",
        "section": "10",
        "areas": ["devils_advocate"],
        "marks": 40,
        "mode_hint": "ic_devils_advocate_pack",
        "question": (
            "Devil's advocate: challenge every major conclusion. For each: supporting evidence, contradicting evidence, "
            "missing evidence, confidence, and what would change your view."
        ),
        "must_include": [
            "supporting",
            "contradict",
            "missing",
            "confidence",
            "change",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O13",
        "section": "11",
        "areas": ["scenario_analysis"],
        "marks": 40,
        "mode_hint": "ic_scenarios_v2",
        "question": (
            "Scenario analysis: create Bull, Base, and Bear cases. For each include revenue, margin, cash flow, "
            "valuation implications, key risks, and key assumptions."
        ),
        "must_include": [
            "bull",
            "base",
            "bear",
            "revenue",
            "margin",
            "cash",
            "assumption",
        ],
        "must_not_include": ["buy", "sell"],
    },
    {
        "id": "O14",
        "section": "12",
        "areas": ["portfolio_decision"],
        "marks": 30,
        "mode_hint": "ic_portfolio_role",
        "question": (
            "Portfolio decision (do not recommend Buy or Sell): what role could this company play in a diversified "
            "portfolio? Which investor profile would find it more or less suitable? Which risks need ongoing monitoring?"
        ),
        "must_include": ["role", "portfolio", "investor profile", "monitor"],
        "must_not_include": ["buy the stock", "sell the stock"],
    },
    {
        "id": "O15",
        "section": "13",
        "areas": ["three_audiences"],
        "marks": 30,
        "mode_hint": "ic_three_audiences",
        "question": (
            "Explain the conclusion for three audiences: a retail investor, a CFA charterholder, and an investment "
            "committee. Facts must remain identical; only communication style changes."
        ),
        "must_include": ["retail", "cfa", "investment committee", "cash"],
        "must_not_include": ["buy now", "sell now"],
    },
    {
        "id": "O16",
        "section": "14",
        "areas": ["audited_only_challenge"],
        "marks": 30,
        "mode_hint": "ic_audited_only",
        "question": (
            "Final challenge: If every valuation model, analyst report and management presentation were removed, "
            "what conclusion could still be supported using only audited financial statements and verified market data?"
        ),
        "must_include": [
            "audited",
            "cash",
            "debt",
            "cannot conclude",
            "market",
        ],
        "must_not_include": ["buy the stock", "sell the stock"],
    },
]

assert sum(int(q["marks"]) for q in QUESTIONS) == TOTAL_RUBRIC_POINTS
assert sum(RUBRIC_AREAS.values()) == TOTAL_RUBRIC_POINTS
assert NEVER_TRAIN is True
