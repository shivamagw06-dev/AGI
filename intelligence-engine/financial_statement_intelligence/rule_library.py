"""Module 4 (Statement Linkage) + Module 6 (Earnings Quality) — a library
of 200+ interpretive relationships.

Every rule fires on ``Deltas`` (period-over-period changes) and, if
triggered, produces a ``Finding`` with the exact numbers as evidence, an
explanation, a severity, and a confidence — never a bare "X changed"
statement. Rules are generated from ~40 ``ComparisonPair`` definitions
(each expanding into up to 5 directional scenarios) plus ~30 standalone
threshold rules, comfortably clearing the 200+ target while staying
maintainable and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from financial_statement_intelligence.deltas import Deltas

_MIN_DIVERGENCE = 0.03  # 3 percentage points minimum to call something "faster/slower"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    module: int
    severity: str  # "positive" | "neutral" | "low" | "medium" | "high"
    confidence: float
    explanation: str
    evidence: dict[str, Optional[float]]


@dataclass(frozen=True)
class InterpretiveRule:
    rule_id: str
    category: str
    module: int
    condition: Callable[[Deltas], bool]
    explain: Callable[[Deltas], str]
    evidence_keys: tuple[str, ...]
    severity: str
    confidence: float = 0.75


def _fmt_pct(x: Optional[float]) -> str:
    return f"{x * 100:+.1f}%" if x is not None else "n/a"


def _evidence(d: Deltas, keys: tuple[str, ...]) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}
    for k in keys:
        item = d.get(k)
        if item:
            out[f"{k}_pct_change"] = item.pct_change
            out[f"{k}_current"] = item.current
    return out


# ---------------------------------------------------------------------------
# Comparison-pair generator (Module 4 + 6 core: "A vs B" relationships)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComparisonPair:
    key: str
    label_a: str
    label_b: str
    metric_a: str
    metric_b: str
    category: str
    module: int
    meaning_a_faster: str
    meaning_b_faster: str
    severity_a_faster: str = "medium"
    severity_b_faster: str = "medium"


COMPARISON_PAIRS: list[ComparisonPair] = [
    ComparisonPair(
        "revenue_vs_ebitda", "Revenue", "EBITDA", "revenue", "ebitda", "operating_leverage", 1,
        "suggests cost inflation or weaker operating leverage — growth is not converting to profit",
        "suggests strong operating leverage — cost discipline is amplifying revenue gains into profit",
        "medium", "positive",
    ),
    ComparisonPair(
        "revenue_vs_receivables", "Revenue", "Receivables", "revenue", "receivables", "earnings_quality", 6,
        "signals improving collections discipline — receivables are keeping pace with sales, not outrunning them",
        "signals collection risk or aggressive revenue recognition — receivables are outpacing the sales that created them",
        "positive", "high",
    ),
    ComparisonPair(
        "revenue_vs_inventory", "Revenue", "Inventory", "revenue", "inventory", "working_capital", 7,
        "signals efficient inventory management — stock is growing slower than sales",
        "may indicate demand slowdown (unsold stock building) or a deliberate strategic build ahead of expected demand",
        "positive", "medium",
    ),
    ComparisonPair(
        "revenue_vs_gross_profit", "Revenue", "Gross Profit", "revenue", "gross_profit", "margin_analysis", 8,
        "implies gross margin compression — costs are eating into the incremental revenue",
        "implies gross margin expansion — improved pricing power or cost control per unit sold",
        "medium", "positive",
    ),
    ComparisonPair(
        "ebitda_vs_capex", "EBITDA", "Capex", "ebitda", "capex", "reinvestment_risk", 6,
        "EBITDA is compounding faster than reinvestment needs — a sign of capital-light scaling",
        "capex is growing much faster than EBITDA — watch for a future depreciation drag on EBIT and PAT",
        "positive", "medium",
    ),
    ComparisonPair(
        "pat_vs_operating_cf", "PAT", "Operating Cash Flow", "pat", "operating_cf", "earnings_quality", 6,
        "weak earnings quality — profit is growing faster than the cash the business actually collects",
        "strong cash conversion — Operating Cash Flow is outpacing reported profit growth",
        "high", "positive",
    ),
    ComparisonPair(
        "ebitda_vs_depreciation", "EBITDA", "Depreciation", "ebitda", "depreciation", "margin_analysis", 1,
        "operating profit is outrunning depreciation growth, widening the EBITDA-to-EBIT bridge favourably",
        "depreciation is rising faster than operating profit, compressing the EBITDA-to-EBIT bridge",
        "positive", "low",
    ),
    ComparisonPair(
        "revenue_vs_payables", "Revenue", "Payables", "revenue", "payables", "working_capital", 7,
        "payables growth is lagging sales — less reliance on supplier financing to fund the business",
        "the business is relying more on supplier financing to fund growth than sales alone would suggest",
        "neutral", "low",
    ),
    ComparisonPair(
        "inventory_vs_payables", "Inventory", "Payables", "inventory", "payables", "working_capital", 7,
        "inventory is building faster than the credit extended by suppliers — a cash-cycle drag",
        "supplier financing is growing faster than inventory build — a cash-cycle tailwind",
        "medium", "positive",
    ),
    ComparisonPair(
        "debt_vs_ebitda", "Total Debt", "EBITDA", "total_debt", "ebitda", "leverage", 5,
        "leverage capacity is deteriorating — debt is growing faster than the earnings base that services it",
        "leverage capacity is improving — EBITDA is growing faster than debt",
        "high", "positive",
    ),
    ComparisonPair(
        "interest_vs_ebit", "Interest Expense", "EBIT", "interest_expense", "ebit", "leverage", 5,
        "interest coverage is shrinking — financing cost is rising faster than operating profit",
        "interest coverage is improving — operating profit is outpacing the cost of debt",
        "high", "positive",
    ),
    ComparisonPair(
        "equity_vs_debt", "Total Equity", "Total Debt", "total_equity", "total_debt", "leverage", 2,
        "the capital structure is de-levering — equity is growing faster than debt",
        "the capital structure is shifting toward debt financing faster than equity is being built",
        "positive", "medium",
    ),
    ComparisonPair(
        "capex_vs_depreciation", "Capex", "Depreciation", "capex", "depreciation", "reinvestment_risk", 3,
        "capex is running well ahead of depreciation — an expansion phase that will raise future depreciation charges",
        "capex is running behind depreciation — the asset base may be ageing without adequate reinvestment",
        "low", "medium",
    ),
    ComparisonPair(
        "dividends_vs_fcf", "Dividends Paid", "Free Cash Flow", "dividends_paid", "free_cash_flow", "dividend_sustainability", 3,
        "the dividend is growing faster than the free cash flow that funds it — a sustainability risk if the gap persists",
        "free cash flow is growing faster than the dividend — increasing dividend coverage and headroom",
        "high", "positive",
    ),
    ComparisonPair(
        "buybacks_vs_fcf", "Buybacks", "Free Cash Flow", "buybacks", "free_cash_flow", "capital_allocation", 3,
        "buybacks are scaling faster than free cash flow generation — check whether they are being funded by debt",
        "free cash flow is growing faster than buyback spend — repurchases remain well within organic capacity",
        "medium", "positive",
    ),
    ComparisonPair(
        "receivable_days_vs_payable_days", "Receivable Days", "Payable Days", "ratio_receivable_days", "ratio_payable_days",
        "working_capital", 7,
        "the cash conversion cycle is lengthening from the receivables side — collections are slowing relative to payment terms",
        "payable days are extending faster than receivable days — this eases the cash conversion cycle but may strain supplier relationships",
        "medium", "low",
    ),
    ComparisonPair(
        "gross_profit_vs_opex", "Gross Profit", "Operating Expenses", "gross_profit", "opex", "margin_analysis", 8,
        "gross profit is scaling faster than operating expenses, expanding EBITDA margin through cost discipline",
        "operating expenses are growing faster than gross profit, compressing EBITDA margin",
        "positive", "medium",
    ),
    ComparisonPair(
        "opex_vs_revenue", "Operating Expenses", "Revenue", "opex", "revenue", "margin_analysis", 8,
        "cost growth is outpacing sales growth — a sign of weakening cost discipline or investment ahead of revenue",
        "revenue is scaling faster than operating costs — genuine operating leverage",
        "medium", "positive",
    ),
    ComparisonPair(
        "revenue_vs_total_assets", "Revenue", "Total Assets", "revenue", "total_assets", "efficiency", 9,
        "revenue is outpacing asset growth — improving asset efficiency (asset turnover)",
        "the asset base is growing faster than revenue — capital intensity is rising, which should show up in ROCE/ROIC",
        "positive", "medium",
    ),
    ComparisonPair(
        "eps_vs_pat", "EPS", "PAT", "eps", "pat", "capital_structure", 1,
        "EPS is growing faster than PAT — buybacks are amplifying the per-share benefit of profit growth",
        "EPS is growing slower than PAT — dilution (new shares issued) is eating into the per-share benefit of profit growth",
        "positive", "medium",
    ),
    ComparisonPair(
        "cash_vs_total_debt", "Cash", "Total Debt", "cash", "total_debt", "leverage", 2,
        "cash is building faster than debt — strengthening net liquidity position",
        "cash is growing slower than debt (or debt is rising while cash is not) — a classic financial-stress signal of liquidity being replaced by borrowing",
        "positive", "high",
    ),
    ComparisonPair(
        "working_capital_vs_revenue", "Working Capital", "Revenue", "working_capital", "revenue", "working_capital", 4,
        "growth is consuming disproportionately more working capital — exactly why PAT can rise while cash flow falls",
        "revenue is scaling with proportionally less working capital consumption — an efficient growth model",
        "medium", "positive",
    ),
    ComparisonPair(
        "roe_vs_pat", "ROE", "PAT", "ratio_roe", "pat", "capital_structure", 5,
        "ROE is improving even as PAT itself is not growing as fast — decompose this via DuPont: it likely reflects a shrinking "
        "equity base (buybacks/dividends) rather than pure operating improvement",
        "PAT is growing faster than ROE would suggest — likely an expanding equity base diluting the ratio despite genuine profit growth",
        "medium", "low",
    ),
    ComparisonPair(
        "roic_vs_debt", "ROIC", "Total Debt", "ratio_roic", "total_debt", "capital_allocation", 5,
        "returns are improving faster than debt is growing — capital efficiency gains look organic rather than leverage-driven",
        "debt is growing faster than ROIC is improving — returns may be increasingly reliant on added leverage rather than "
        "genuine capital efficiency",
        "positive", "medium",
    ),
    ComparisonPair(
        "treasury_stock_vs_share_capital", "Treasury Stock", "Share Capital", "treasury_stock", "share_capital",
        "capital_structure", 2,
        "buyback activity (treasury stock) is scaling faster than new capital raised — a net capital-return posture",
        "new share capital is being raised faster than buybacks — a net capital-raising posture, potentially diluting existing holders",
        "positive", "medium",
    ),
    ComparisonPair(
        "cash_vs_revenue", "Cash", "Revenue", "cash", "revenue", "cash_generation", 3,
        "cash balance is building faster than revenue — strong underlying cash generation beyond top-line growth alone",
        "revenue is growing faster than the cash balance — check whether working capital or capex is absorbing the difference",
        "positive", "low",
    ),
    ComparisonPair(
        "lease_vs_total_debt", "Lease Liabilities", "Total Debt", "lease_liabilities", "total_debt", "leverage", 2,
        "lease liabilities are growing faster than on-balance-sheet debt — true leverage may be understated by headline debt metrics alone",
        "on-balance-sheet debt is growing faster than lease liabilities — leverage growth is more transparent, not hidden in leases",
        "medium", "low",
    ),
    ComparisonPair(
        "intangibles_vs_total_assets", "Intangibles", "Total Assets", "intangibles", "total_assets", "asset_quality", 2,
        "intangible assets are growing faster than the overall asset base — asset quality is shifting toward less tangible, "
        "harder-to-value assets",
        "the tangible asset base is growing faster than intangibles — a more conservative asset mix shift",
        "medium", "low",
    ),
    ComparisonPair(
        "goodwill_vs_total_assets", "Goodwill", "Total Assets", "goodwill", "total_assets", "acquisition_risk", 2,
        "goodwill is growing faster than total assets — likely from acquisitions, concentrating impairment risk on the balance sheet",
        "total assets are growing faster than goodwill — acquisition-driven risk concentration is easing relative to the balance sheet",
        "medium", "low",
    ),
    ComparisonPair(
        "share_capital_vs_pat", "Share Capital", "PAT", "share_capital", "pat", "capital_structure", 2,
        "new equity is being raised faster than profit is growing — growth may be increasingly externally funded rather than "
        "internally generated",
        "profit is growing faster than share capital — growth is increasingly self-funded rather than reliant on new equity raises",
        "medium", "positive",
    ),
    ComparisonPair(
        "receivables_vs_inventory", "Receivables", "Inventory", "receivables", "inventory", "working_capital", 7,
        "receivables are growing faster than inventory — the working-capital drag is shifting toward the collections side",
        "inventory is growing faster than receivables — the working-capital drag is shifting toward the stocking side",
        "low", "low",
    ),
    ComparisonPair(
        "ppe_vs_depreciation", "Net PPE", "Depreciation", "ppe_net", "depreciation", "reinvestment_risk", 2,
        "the net fixed-asset base is growing faster than depreciation — an active expansion phase",
        "depreciation is outpacing net PPE growth — the asset base may be shrinking or ageing faster than it is replaced",
        "positive", "medium",
    ),
    ComparisonPair(
        "total_assets_vs_revenue", "Total Assets", "Revenue", "total_assets", "revenue", "efficiency", 9,
        "the balance sheet is growing faster than the top line — capital intensity is rising",
        "revenue is scaling faster than the balance sheet — capital efficiency is improving",
        "medium", "positive",
    ),
    ComparisonPair(
        "financing_cf_vs_investing_cf", "Financing Cash Flow", "Investing Cash Flow", "financing_cf", "investing_cf",
        "capital_allocation", 3,
        "external financing is growing faster than investment activity — funding is outpacing where it is being deployed",
        "investment activity is scaling faster than external financing — growth is being funded more from internal sources",
        "low", "positive",
    ),
    ComparisonPair(
        "operating_cf_vs_revenue", "Operating Cash Flow", "Revenue", "operating_cf", "revenue", "cash_generation", 3,
        "operating cash flow is growing faster than revenue — an improving cash-conversion rate",
        "revenue is growing faster than the cash it generates — a widening cash-conversion gap",
        "positive", "medium",
    ),
    ComparisonPair(
        "gross_profit_vs_cogs", "Gross Profit", "COGS", "gross_profit", "cogs", "cost_structure", 8,
        "gross profit is scaling faster than COGS — pricing power or input-cost relief is driving margin expansion",
        "cost of goods sold is rising faster than gross profit — input cost pressure is outpacing pricing/volume gains",
        "positive", "medium",
    ),
    ComparisonPair(
        "debt_repaid_vs_debt_raised", "Debt Repaid", "Debt Raised", "debt_repaid", "debt_raised", "leverage", 3,
        "the pace of deleveraging (repayment) is accelerating relative to new borrowing — a deliberate deleveraging posture",
        "new borrowing is accelerating relative to repayment — a releveraging posture worth monitoring against EBITDA capacity",
        "positive", "medium",
    ),
    ComparisonPair(
        "short_term_debt_vs_long_term_debt", "Short-term Debt", "Long-term Debt", "short_term_debt", "long_term_debt",
        "leverage", 2,
        "the debt maturity profile is shortening — more refinancing risk concentrated in the near term",
        "the debt maturity profile is lengthening — refinancing risk is being pushed further out, generally a healthier structure",
        "medium", "positive",
    ),
    ComparisonPair(
        "eps_vs_revenue", "EPS", "Revenue", "eps", "revenue", "growth_quality", 1,
        "EPS is growing faster than revenue — margin expansion and/or buybacks are amplifying top-line growth into per-share value",
        "EPS is growing slower than revenue — margin compression or dilution is eating into the per-share translation of top-line growth",
        "positive", "medium",
    ),
    ComparisonPair(
        "total_liabilities_vs_total_assets", "Total Liabilities", "Total Assets", "total_liabilities", "total_assets",
        "leverage", 2,
        "liabilities are growing faster than assets — balance-sheet gearing is increasing",
        "assets are growing faster than liabilities — balance-sheet gearing is decreasing, strengthening the equity cushion",
        "medium", "positive",
    ),
]


def _make_pair_rules(pair: ComparisonPair) -> list[InterpretiveRule]:
    rules: list[InterpretiveRule] = []
    a, b = pair.metric_a, pair.metric_b
    keys = (a, b)

    def pct_a(d: Deltas) -> Optional[float]:
        return d.pct(a)

    def pct_b(d: Deltas) -> Optional[float]:
        return d.pct(b)

    def both_present(d: Deltas) -> bool:
        return pct_a(d) is not None and pct_b(d) is not None

    # 1. Both up, A grew faster than B by more than the minimum divergence.
    rules.append(
        InterpretiveRule(
            f"{pair.key}__a_faster", pair.category, pair.module,
            lambda d: both_present(d) and pct_a(d) > 0 and pct_b(d) > 0 and pct_a(d) - pct_b(d) > _MIN_DIVERGENCE,
            lambda d: f"{pair.label_a} grew {_fmt_pct(pct_a(d))} while {pair.label_b} grew only {_fmt_pct(pct_b(d))} — {pair.meaning_a_faster}.",
            keys, pair.severity_a_faster,
        )
    )
    # 2. Both up, B grew faster than A.
    rules.append(
        InterpretiveRule(
            f"{pair.key}__b_faster", pair.category, pair.module,
            lambda d: both_present(d) and pct_a(d) > 0 and pct_b(d) > 0 and pct_b(d) - pct_a(d) > _MIN_DIVERGENCE,
            lambda d: f"{pair.label_b} grew {_fmt_pct(pct_b(d))} while {pair.label_a} grew only {_fmt_pct(pct_a(d))} — {pair.meaning_b_faster}.",
            keys, pair.severity_b_faster,
        )
    )
    # 3. A up, B down.
    rules.append(
        InterpretiveRule(
            f"{pair.key}__a_up_b_down", pair.category, pair.module,
            lambda d: both_present(d) and pct_a(d) > 0 and pct_b(d) < -_MIN_DIVERGENCE,
            lambda d: f"{pair.label_a} increased {_fmt_pct(pct_a(d))} while {pair.label_b} declined {_fmt_pct(pct_b(d))} — {pair.meaning_a_faster}.",
            keys, pair.severity_a_faster,
        )
    )
    # 4. B up, A down.
    rules.append(
        InterpretiveRule(
            f"{pair.key}__b_up_a_down", pair.category, pair.module,
            lambda d: both_present(d) and pct_b(d) > 0 and pct_a(d) < -_MIN_DIVERGENCE,
            lambda d: f"{pair.label_b} increased {_fmt_pct(pct_b(d))} while {pair.label_a} declined {_fmt_pct(pct_a(d))} — {pair.meaning_b_faster}.",
            keys, pair.severity_b_faster,
        )
    )
    # 5. Both down — deliberately NEUTRAL/DESCRIPTIVE ONLY. Unlike the four
    # scenarios above, "both declined" does not have a single safe polarity
    # across all 40 pairs: for a value-pair (Revenue vs EBITDA) both falling
    # is bad; for a cost-pair (Gross Profit vs Opex) Opex falling is GOOD.
    # Asserting "both metrics deteriorated" here would be wrong roughly half
    # the time — so this rule reports the fact and explicitly defers to the
    # pair's own context instead of guessing a polarity.
    rules.append(
        InterpretiveRule(
            f"{pair.key}__both_down", pair.category, pair.module,
            lambda d: both_present(d) and pct_a(d) < 0 and pct_b(d) < 0,
            lambda d: (
                f"{pair.label_a} fell {_fmt_pct(pct_a(d))} and {pair.label_b} fell {_fmt_pct(pct_b(d))} in the "
                f"same period — whether this is favourable depends on what {pair.label_b} represents: a "
                f"decline is a positive signal if {pair.label_b} is a cost/expense/working-capital item "
                f"({pair.meaning_b_faster.split(' — ')[0] if '—' not in pair.meaning_b_faster else pair.meaning_b_faster}), "
                f"and a negative signal if it represents value creation."
            ),
            keys, "neutral", 0.5,
        )
    )
    return rules


def _pair_generated_rules() -> list[InterpretiveRule]:
    out: list[InterpretiveRule] = []
    for pair in COMPARISON_PAIRS:
        out.extend(_make_pair_rules(pair))
    return out


# ---------------------------------------------------------------------------
# Standalone threshold rules (single-metric warning signs, Module 5/10)
# ---------------------------------------------------------------------------
def _std(rule_id, category, module, condition, explain, keys, severity, confidence=0.8) -> InterpretiveRule:
    return InterpretiveRule(rule_id, category, module, condition, explain, keys, severity, confidence)


def _ratio(d: Deltas, key: str) -> Optional[float]:
    item = d.get(f"ratio_{key}")
    return item.current if item else None


def _ratio_pct(d: Deltas, key: str) -> Optional[float]:
    item = d.get(f"ratio_{key}")
    return item.pct_change if item else None


STANDALONE_RULES: list[InterpretiveRule] = [
    _std("liquidity_current_ratio_below_1", "liquidity", 5,
         lambda d: (_ratio(d, "current_ratio") or 99) < 1.0,
         lambda d: f"Current Ratio of {_ratio(d, 'current_ratio'):.2f}x is below 1.0x — current liabilities exceed current assets.",
         ("ratio_current_ratio",), "high"),
    _std("liquidity_quick_ratio_below_1", "liquidity", 5,
         lambda d: (_ratio(d, "quick_ratio") or 99) < 1.0,
         lambda d: f"Quick Ratio of {_ratio(d, 'quick_ratio'):.2f}x is below 1.0x — near-term liquidity depends on selling inventory.",
         ("ratio_quick_ratio",), "medium"),
    _std("liquidity_cash_ratio_below_0_2", "liquidity", 5,
         lambda d: (_ratio(d, "cash_ratio") or 99) < 0.2,
         lambda d: f"Cash Ratio of {_ratio(d, 'cash_ratio'):.2f}x is below 0.2x — a thin cash cushion against current liabilities.",
         ("ratio_cash_ratio",), "low"),
    _std("leverage_debt_equity_above_1_5", "leverage", 5,
         lambda d: (_ratio(d, "debt_to_equity") or 0) > 1.5,
         lambda d: f"Debt/Equity of {_ratio(d, 'debt_to_equity'):.2f}x is above the 1.5x caution threshold.",
         ("ratio_debt_to_equity",), "medium"),
    _std("leverage_net_debt_ebitda_above_3_5", "leverage", 5,
         lambda d: (_ratio(d, "net_debt_to_ebitda") or 0) > 3.5,
         lambda d: f"Net Debt/EBITDA of {_ratio(d, 'net_debt_to_ebitda'):.2f}x is above the 3.5x caution threshold for a non-financial business.",
         ("ratio_net_debt_to_ebitda",), "high"),
    _std("leverage_interest_coverage_below_2", "leverage", 5,
         lambda d: (_ratio(d, "interest_coverage") or 99) < 2.0,
         lambda d: f"Interest Coverage of {_ratio(d, 'interest_coverage'):.2f}x is below the 2.0x caution threshold.",
         ("ratio_interest_coverage",), "high"),
    _std("leverage_interest_coverage_below_1", "leverage", 5,
         lambda d: (_ratio(d, "interest_coverage") or 99) < 1.0,
         lambda d: f"Interest Coverage of {_ratio(d, 'interest_coverage'):.2f}x is below 1.0x — EBIT does not even cover interest expense.",
         ("ratio_interest_coverage",), "high", 0.9),
    _std("working_capital_ccc_above_100", "working_capital", 7,
         lambda d: (_ratio(d, "cash_conversion_cycle") or 0) > 100,
         lambda d: f"Cash Conversion Cycle of {_ratio(d, 'cash_conversion_cycle'):.0f} days is above the 100-day caution threshold.",
         ("ratio_cash_conversion_cycle",), "medium"),
    _std("working_capital_receivable_days_above_90", "working_capital", 7,
         lambda d: (_ratio(d, "receivable_days") or 0) > 90,
         lambda d: f"Receivable Days of {_ratio(d, 'receivable_days'):.0f} is above 90 days — extended customer credit or collection risk.",
         ("ratio_receivable_days",), "medium"),
    _std("working_capital_inventory_days_above_120", "working_capital", 7,
         lambda d: (_ratio(d, "inventory_days") or 0) > 120,
         lambda d: f"Inventory Days of {_ratio(d, 'inventory_days'):.0f} is above 120 days — slow-moving stock or a strategic build.",
         ("ratio_inventory_days",), "medium"),
    _std("working_capital_payable_days_spike", "working_capital", 7,
         lambda d: (_ratio_pct(d, "payable_days") or 0) > 0.30,
         lambda d: f"Payable Days extended {_fmt_pct(_ratio_pct(d, 'payable_days'))} in one period — a sharp stretch of supplier terms, "
                    f"which can be efficient management or a sign of cash stress.",
         ("ratio_payable_days",), "low"),
    _std("margin_gross_margin_declining", "margin_analysis", 8,
         lambda d: (_ratio(d, "gross_margin") or 0) > 0 and (_ratio_pct(d, "gross_margin") or 0) < -0.05,
         lambda d: f"Gross Margin declined {_fmt_pct(_ratio_pct(d, 'gross_margin'))} — pricing, mix, or input costs are pressuring "
                    f"unit economics.",
         ("ratio_gross_margin",), "medium"),
    _std("margin_ebitda_margin_declining", "margin_analysis", 8,
         lambda d: (_ratio_pct(d, "ebitda_margin") or 0) < -0.05,
         lambda d: f"EBITDA Margin declined {_fmt_pct(_ratio_pct(d, 'ebitda_margin'))} — operating leverage is working against the business.",
         ("ratio_ebitda_margin",), "medium"),
    _std("margin_operating_margin_declining", "margin_analysis", 8,
         lambda d: (_ratio_pct(d, "operating_margin") or 0) < -0.05,
         lambda d: f"Operating Margin declined {_fmt_pct(_ratio_pct(d, 'operating_margin'))} — check whether depreciation or "
                    f"EBITDA margin is the driver.",
         ("ratio_operating_margin",), "medium"),
    _std("margin_net_margin_declining", "margin_analysis", 8,
         lambda d: (_ratio_pct(d, "net_margin") or 0) < -0.05,
         lambda d: f"Net Margin declined {_fmt_pct(_ratio_pct(d, 'net_margin'))} — check operating margin, interest burden, "
                    f"and effective tax rate for the driver.",
         ("ratio_net_margin",), "medium"),
    _std("profitability_roe_declining", "profitability", 5,
         lambda d: (_ratio_pct(d, "roe") or 0) < -0.10,
         lambda d: f"ROE declined {_fmt_pct(_ratio_pct(d, 'roe'))} — decompose via margin, turnover, and leverage to isolate the driver.",
         ("ratio_roe",), "medium"),
    _std("profitability_roic_below_hurdle", "capital_allocation", 5,
         lambda d: (_ratio(d, "roic") or 99) < 0.10,
         lambda d: f"ROIC of {_fmt_pct(_ratio(d, 'roic'))} is below a typical 10% cost-of-capital proxy — incremental capital may "
                    f"not be earning its keep.",
         ("ratio_roic",), "medium"),
    _std("asset_quality_goodwill_concentration", "acquisition_risk", 2,
         lambda d: (d.level("goodwill") or 0) > 0.30 * (d.level("total_assets") or 1),
         lambda d: f"Goodwill of {d.level('goodwill'):,.0f} is over 30% of Total Assets ({d.level('total_assets'):,.0f}) — "
                    f"impairment risk is concentrated on the balance sheet.",
         ("goodwill", "total_assets"), "medium"),
    _std("asset_quality_intangibles_concentration", "asset_quality", 2,
         lambda d: (d.level("intangibles") or 0) > 0.40 * (d.level("total_assets") or 1),
         lambda d: f"Intangibles of {d.level('intangibles'):,.0f} are over 40% of Total Assets — asset quality skews toward "
                    f"harder-to-value assets.",
         ("intangibles", "total_assets"), "low"),
    _std("dilution_shares_up_eps_down", "capital_structure", 1,
         lambda d: (d.pct("share_capital") or 0) > _MIN_DIVERGENCE and (d.pct("eps") or 0) < 0,
         lambda d: f"Share Capital increased {_fmt_pct(d.pct('share_capital'))} while EPS declined {_fmt_pct(d.pct('eps'))} — "
                    f"dilution is outpacing profit growth on a per-share basis.",
         ("share_capital", "eps"), "medium"),
    _std("cash_flow_negative_fcf", "cash_generation", 3,
         lambda d: (d.level("free_cash_flow") or 0) < 0,
         lambda d: f"Free Cash Flow is negative ({d.level('free_cash_flow'):,.0f}) — the business is consuming more cash in "
                    f"operations and capex than it generates.",
         ("free_cash_flow",), "high"),
    _std("cash_flow_negative_ocf", "cash_generation", 3,
         lambda d: (d.level("operating_cf") or 0) < 0,
         lambda d: f"Operating Cash Flow is negative ({d.level('operating_cf'):,.0f}) — core operations are consuming cash, "
                    f"regardless of reported PAT.",
         ("operating_cf",), "high", 0.9),
    _std("reinvestment_capex_depreciation_high", "reinvestment_risk", 3,
         lambda d: (d.level("depreciation") or 0) > 0 and (d.level("capex") or 0) / (d.level("depreciation") or 1) > 2.0,
         lambda d: f"Capex is {(d.level('capex') or 0) / (d.level('depreciation') or 1):.1f}x Depreciation — an active expansion "
                    f"phase that will raise future depreciation charges.",
         ("capex", "depreciation"), "low"),
    _std("reinvestment_capex_depreciation_low", "reinvestment_risk", 3,
         lambda d: (d.level("depreciation") or 0) > 0 and (d.level("capex") or 0) / (d.level("depreciation") or 1) < 0.7,
         lambda d: f"Capex is only {(d.level('capex') or 0) / (d.level('depreciation') or 1):.1f}x Depreciation — the asset base "
                    f"may be ageing faster than it is being replaced.",
         ("capex", "depreciation"), "medium"),
    _std("tax_rate_spike", "income_statement", 1,
         lambda d: (d.get("tax_rate").pct_change or 0) is not None and (d.get("tax_rate").abs_change or 0) > 0.05
         if d.get("tax_rate") else False,
         lambda d: f"Effective tax rate rose {(d.get('tax_rate').abs_change or 0) * 100:.1f} percentage points — reducing PAT "
                    f"independent of operating performance.",
         ("tax_rate",), "low"),
    _std("tax_rate_drop", "income_statement", 1,
         lambda d: (d.get("tax_rate").abs_change or 0) < -0.05 if d.get("tax_rate") else False,
         lambda d: f"Effective tax rate fell {abs((d.get('tax_rate').abs_change or 0)) * 100:.1f} percentage points — boosting "
                    f"PAT independent of operating performance; check for one-off tax credits.",
         ("tax_rate",), "low"),
    _std("buyback_possibly_debt_funded", "capital_allocation", 3,
         lambda d: (d.level("buybacks") or 0) > 0 and (d.pct("total_debt") or 0) > 0.05,
         lambda d: f"Buybacks of {d.level('buybacks'):,.0f} occurred alongside a {_fmt_pct(d.pct('total_debt'))} rise in Total "
                    f"Debt — verify the repurchase is not debt-funded.",
         ("buybacks", "total_debt"), "medium"),
    _std("dividend_possibly_debt_funded", "dividend_sustainability", 3,
         lambda d: (d.level("dividends_paid") or 0) > (d.level("free_cash_flow") or 0) > float("-inf")
         and (d.level("free_cash_flow") or 1) < (d.level("dividends_paid") or 0),
         lambda d: f"Dividends paid ({d.level('dividends_paid'):,.0f}) exceed Free Cash Flow ({d.level('free_cash_flow'):,.0f}) "
                    f"this period — the payout is not fully covered by cash generated.",
         ("dividends_paid", "free_cash_flow"), "high"),
    _std("debt_maturity_shortening", "leverage", 2,
         lambda d: (d.pct("short_term_debt") or 0) > 0.15 and (d.pct("long_term_debt") or 0) < 0,
         lambda d: f"Short-term Debt grew {_fmt_pct(d.pct('short_term_debt'))} while Long-term Debt declined "
                    f"{_fmt_pct(d.pct('long_term_debt'))} — the maturity profile is shortening, raising refinancing risk.",
         ("short_term_debt", "long_term_debt"), "medium"),
]


def build_rule_library() -> list[InterpretiveRule]:
    return _pair_generated_rules() + list(STANDALONE_RULES)


_LIBRARY_CACHE: list[InterpretiveRule] | None = None


def rule_library() -> list[InterpretiveRule]:
    global _LIBRARY_CACHE
    if _LIBRARY_CACHE is None:
        _LIBRARY_CACHE = build_rule_library()
    return _LIBRARY_CACHE


def evaluate_rules(deltas: Deltas) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rule_library():
        try:
            if rule.condition(deltas):
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        category=rule.category,
                        module=rule.module,
                        severity=rule.severity,
                        confidence=rule.confidence,
                        explanation=rule.explain(deltas),
                        evidence=_evidence(deltas, rule.evidence_keys),
                    )
                )
        except (TypeError, ZeroDivisionError, AttributeError):
            continue
    return findings
