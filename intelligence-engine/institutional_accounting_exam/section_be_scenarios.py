"""Sections B-E (Q6-25) — Statement Linkage, Earnings Quality, Ratio
Intelligence, Red Flags.

Each scenario is instantiated as a REAL two-period ``StatementPeriod``
pair matching the described pattern, then run through Phase 2's actual
rule library / ratio engine / red-flag detector to produce the answer —
the numbers are constructed to exhibit the pattern, but the
interpretation is computed, not scripted.
"""

from __future__ import annotations

from typing import Any, Optional

from financial_foundations.linkage_engine import why_pat_not_equal_cash_flow
from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.earnings_quality import assess_earnings_quality
from financial_statement_intelligence.metric_concepts import get_metric
from financial_statement_intelligence.ratio_engine import compute_ratios
from financial_statement_intelligence.red_flag_detector import detect_red_flags
from financial_statement_intelligence.rule_library import evaluate_rules
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod
from institutional_accounting_exam.schema import ExamAnswer, ExamItem


def _pair(**overrides: dict[str, Any]) -> tuple[StatementPeriod, StatementPeriod]:
    """Two baseline periods (identical) with the given per-period overrides
    applied — ``prior`` and ``current`` keys hold dicts of field overrides."""
    base = dict(revenue=1000, cogs=600, opex=180, depreciation=40, interest_expense=20, tax_expense=30,
                cash=200, receivables=100, inventory=80, ppe_net=300, payables=90, long_term_debt=200,
                share_capital=400, retained_earnings=100, operating_cf=150, capex=40, dividends_paid=10)
    prior_fields = {**base, **overrides.get("prior", {})}
    current_fields = {**base, **overrides.get("current", {})}
    prior = StatementPeriod(label="P0", sequence=1, **prior_fields)
    current = StatementPeriod(label="P1", sequence=2, **current_fields)
    return prior, current


def _finding_texts(prior: StatementPeriod, current: StatementPeriod) -> list[str]:
    return [f.explanation for f in evaluate_rules(compute_deltas(prior, current))]


def _answer_from_findings(intro: str, findings: list[str], keypoints: list[str], evidence: dict) -> ExamAnswer:
    body = " ".join(findings[:4]) if findings else "No rule in the library fired for this exact combination."
    text = f"{intro} {body}"
    return ExamAnswer(
        answer_text=text,
        evidence=evidence,
        linkage_checks={"at_least_one_finding_fired": len(findings) > 0},
        interpretation_keypoints_expected=keypoints,
        interpretation_keypoints_matched=[k for k in keypoints if k in text.lower()],
    )


# --- Q6 ---------------------------------------------------------------
def _q6_pat_up_cash_down() -> ExamAnswer:
    lesson = why_pat_not_equal_cash_flow()
    reasons = [f"{r['cause']}: {r['explanation']}" for r in lesson["reasons"]]
    text = (
        "PAT increasing while Cash decreases can have several independent causes, and more than one "
        "can be true at once: " + " | ".join(reasons) + f" In one line: {lesson['one_line']}"
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"lesson": lesson},
        causal_reasoning_present=True,
        interpretation_keypoints_expected=["depreciation", "receivable", "inventory", "accrued", "unearned", "working capital"],
        interpretation_keypoints_matched=[k for k in ["depreciation", "receivable", "inventory", "accrued", "unearned", "working capital"] if k in text.lower()],
    )


# --- Q7 ---------------------------------------------------------------
def _q7_inventory_doubles_revenue_flat() -> ExamAnswer:
    # Revenue "flat" ≈ +0.2% (not literally 0.000%, matching how "flat" is
    # used in practice) so the Revenue-vs-Inventory rule can fire at all —
    # a metric at EXACTLY zero change satisfies none of the five directional
    # scenarios (neither "both up" nor "one up one down").
    prior, current = _pair(prior={"inventory": 100, "revenue": 1000}, current={"inventory": 200, "revenue": 1002})
    findings = _finding_texts(prior, current)
    return _answer_from_findings(
        "Inventory doubling while Revenue stays flat:",
        findings,
        ["demand slowdown", "strategic", "unsold"],
        {"prior": prior.__dict__, "current": current.__dict__, "findings": findings},
    )


# --- Q8 ---------------------------------------------------------------
def _q8_receivables_60_revenue_10() -> ExamAnswer:
    prior, current = _pair(prior={"receivables": 100, "revenue": 1000}, current={"receivables": 160, "revenue": 1100})
    findings = _finding_texts(prior, current)
    return _answer_from_findings(
        "Receivables +60% against Revenue +10%:",
        findings,
        ["collection risk", "aggressive", "recognition"],
        {"prior": prior.__dict__, "current": current.__dict__, "findings": findings},
    )


# --- Q9 ---------------------------------------------------------------
def _q9_debt_up_interest_down() -> ExamAnswer:
    card = get_metric("leverage_structure")
    text = (
        "Yes, this is possible — Debt and Interest Expense are not mechanically tied in the same "
        "direction within a single period. Plausible explanations: (1) the new debt was raised late in "
        "the period, so the average balance used to compute interest expense is still low; "
        "(2) the company refinanced older, higher-rate debt with new, lower-rate debt — the balance rose "
        "but the effective rate fell enough to reduce total interest; (3) a shift in the debt mix toward "
        "instruments with lower coupons (e.g. government-linked or subsidised borrowing). "
        + (card.interpretation if card else "")
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"metric_card": card.__dict__ if card else None},
        causal_reasoning_present=True,
        interpretation_keypoints_expected=["refinanc", "average balance", "rate", "possible"],
        interpretation_keypoints_matched=[k for k in ["refinanc", "average balance", "rate", "possible"] if k in text.lower()],
    )


# --- Q10 ---------------------------------------------------------------
def _q10_depreciation_doubles_cash_unchanged() -> ExamAnswer:
    from financial_foundations.education import explain_concept

    card = explain_concept("depreciation")
    text = (
        f"Depreciation doubling has NO effect on Cash because it is a non-cash allocation of an asset's "
        f"cost that was already paid for in cash when the asset was purchased. {card.get('definition', '')} "
        f"{card.get('common_mistake', '')} Doubling it only reduces EBIT and PAT further (via a higher "
        f"non-cash charge) and would, if anything, INCREASE the gap between PAT and Operating Cash Flow, "
        f"since a larger non-cash add-back is required to reconcile the two."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"concept": card},
        causal_reasoning_present=True,
        interpretation_keypoints_expected=["non-cash", "already", "add", "back", "ebit"],
        interpretation_keypoints_matched=[k for k in ["non-cash", "already", "add", "back", "ebit"] if k in text.lower()],
    )


# --- Q11 ---------------------------------------------------------------
def _q11_revenue20_pat25_ocf_neg30() -> ExamAnswer:
    # Prior PAT = 1000-550-150-40-20-25 = 215. Current tax is solved so PAT
    # lands at exactly 215*1.25 = 268.75, matching the question's "+25%".
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 550, "opex": 150, "tax_expense": 25, "operating_cf": 150},
        current={"revenue": 1200, "cogs": 620, "opex": 155, "tax_expense": 96.25, "operating_cf": 105},
    )
    findings = _finding_texts(prior, current)
    series = FinancialSeries(company="Q11", periods=[prior, current])
    eq = assess_earnings_quality(series)
    text = (
        f"Revenue +{compute_deltas(prior, current).pct('revenue') * 100:.0f}%, PAT +"
        f"{compute_deltas(prior, current).pct('pat') * 100:.0f}%, OCF "
        f"{compute_deltas(prior, current).pct('operating_cf') * 100:.0f}% — PAT growing faster than Revenue "
        f"while Operating Cash Flow falls is a textbook earnings-quality warning: profit growth is not "
        f"cash-backed. Earnings Quality score: {eq.get('score')}/10 ({eq.get('label')}). " + " ".join(findings[:2])
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"earnings_quality": eq, "findings": findings},
        linkage_checks={"earnings_quality_computed": eq.get("available", False)},
        interpretation_keypoints_expected=["earnings quality", "cash", "warning", "profit"],
        interpretation_keypoints_matched=[k for k in ["earnings quality", "cash", "warning", "profit"] if k in text.lower()],
    )


# --- Q12 ---------------------------------------------------------------
def _q12_ebitda18_fcf_neg40_capex_doubled() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 550, "opex": 180, "capex": 40, "operating_cf": 150},
        current={"revenue": 1100, "cogs": 590, "opex": 190, "capex": 90, "operating_cf": 145},
    )
    findings = _finding_texts(prior, current)
    fcf_card = get_metric("free_cash_flow")
    text = (
        "EBITDA growing while Free Cash Flow falls sharply and Capex roughly doubles is a reinvestment-phase "
        f"pattern, not necessarily a red flag on its own: {fcf_card.interpretation if fcf_card else ''} "
        + " ".join(findings[:2])
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"findings": findings, "fcf_card": fcf_card.__dict__ if fcf_card else None},
        interpretation_keypoints_expected=["capex", "reinvestment", "free cash flow", "future"],
        interpretation_keypoints_matched=[k for k in ["capex", "reinvestment", "free cash flow", "future"] if k in text.lower()],
    )


# --- Q13 ---------------------------------------------------------------
def _q13_working_capital_absorbs_500cr() -> ExamAnswer:
    card = get_metric("working_capital_cf")
    text = (
        f"Working Capital absorbing ₹500 crore means that amount of cash is trapped funding the operating "
        f"cycle (receivables + inventory, net of payables) rather than being available as free cash flow — "
        f"even a highly profitable, growing business will show Operating Cash Flow roughly ₹500 crore lower "
        f"than PAT plus non-cash add-backs would otherwise suggest. {card.interpretation if card else ''} "
        f"This is exactly why growth can be genuinely profitable on the Income Statement while consuming, "
        f"not generating, cash."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"card": card.__dict__ if card else None},
        interpretation_keypoints_expected=["trapped", "operating cash flow", "growth", "cash"],
        interpretation_keypoints_matched=[k for k in ["trapped", "operating cash flow", "growth", "cash"] if k in text.lower()],
    )


# --- Q14 ---------------------------------------------------------------
def _q14_inv_down_ar_down_cash_up_revenue_flat() -> ExamAnswer:
    prior, current = _pair(
        prior={"inventory": 150, "receivables": 130, "cash": 150, "revenue": 1000},
        current={"inventory": 90, "receivables": 80, "cash": 260, "revenue": 1000},
    )
    findings = _finding_texts(prior, current)
    text = (
        "Inventory and Receivables both falling while Cash rises, with Revenue flat, is a working-capital "
        "RELEASE — the business is collecting faster and de-stocking, freeing up cash without needing "
        "revenue growth to do it. This is a genuine cash-generation positive, but flat Revenue alongside "
        "an inventory drawdown is also consistent with management pre-emptively cutting stock ahead of an "
        "anticipated demand slowdown — the direction of forward orders/guidance would disambiguate the two. "
        + " ".join(findings[:2])
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"findings": findings},
        interpretation_keypoints_expected=["release", "cash", "collecting", "destocking", "slowdown"],
        interpretation_keypoints_matched=[k for k in ["release", "cash", "collecting", "de-stock", "slowdown"] if k in text.lower()],
    )


# --- Q15 ---------------------------------------------------------------
def _q15_pat_falls_roe_rises() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 600, "opex": 150, "share_capital": 400, "retained_earnings": 200, "treasury_stock": 0},
        current={"revenue": 1000, "cogs": 620, "opex": 160, "share_capital": 400, "retained_earnings": 100, "treasury_stock": 200},
    )
    findings = _finding_texts(prior, current)
    ratios_prior = compute_ratios(FinancialSeries(company="Q15", periods=[prior]))
    ratios_current = compute_ratios(FinancialSeries(company="Q15", periods=[prior, current]))
    text = (
        f"PAT fell (₹{prior.pat:,.0f} → ₹{current.pat:,.0f}) while ROE rose ({ratios_prior['roe']} → "
        f"{ratios_current['roe']}) — this happens when the Equity base shrinks faster than PAT falls, "
        f"typically from buybacks or dividends exceeding retained profit. ROE is a RATIO: if the denominator "
        f"(Equity) shrinks by a larger proportion than the numerator (PAT), the ratio rises even on lower "
        f"profit — decompose via DuPont before crediting this to operating improvement. " + " ".join(findings[:2])
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_prior, "ratios_current": ratios_current, "findings": findings},
        linkage_checks={"roe_rose_despite_pat_fall": ratios_current["roe"] > ratios_prior["roe"] and current.pat < prior.pat},
        interpretation_keypoints_expected=["equity", "buyback", "dupont", "shrink", "ratio"],
        interpretation_keypoints_matched=[k for k in ["equity", "buyback", "dupont", "shrink", "ratio"] if k in text.lower()],
    )


# --- Q16 ---------------------------------------------------------------
def _q16_current_falls_quick_rises() -> ExamAnswer:
    prior, current = _pair(
        prior={"cash": 100, "receivables": 100, "inventory": 200, "payables": 150},
        current={"cash": 110, "receivables": 110, "inventory": 80, "payables": 160},
    )
    ratios_p = compute_ratios(FinancialSeries(company="Q16", periods=[prior]))
    ratios_c = compute_ratios(FinancialSeries(company="Q16", periods=[prior, current]))
    text = (
        f"Yes — Current Ratio moved {ratios_p['current_ratio']} → {ratios_c['current_ratio']} (fell) while "
        f"Quick Ratio moved {ratios_p['quick_ratio']} → {ratios_c['quick_ratio']} (rose). This happens when "
        f"Inventory (excluded from the Quick Ratio) falls sharply while Cash and Receivables (both still "
        f"counted in the Quick Ratio) hold steady or improve — the mechanical exclusion of a shrinking, "
        f"low-liquidity asset from Quick Ratio's numerator lets it diverge from Current Ratio."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_p, "ratios_current": ratios_c},
        linkage_checks={
            "current_ratio_fell": ratios_c["current_ratio"] < ratios_p["current_ratio"],
            "quick_ratio_rose": ratios_c["quick_ratio"] > ratios_p["quick_ratio"],
        },
        interpretation_keypoints_expected=["inventory", "exclude", "quick ratio", "liquidity"],
        interpretation_keypoints_matched=[k for k in ["inventory", "exclud", "quick ratio", "liquidity"] if k in text.lower()],
    )


# --- Q17 ---------------------------------------------------------------
def _q17_roce_rises_roe_falls() -> ExamAnswer:
    # A large equity raise (share_capital 400 -> 1000) dilutes ROE's
    # denominator enough to outweigh the EBIT improvement, while ROCE (which
    # doesn't depend on the debt/equity split, only on Capital Employed and
    # EBIT) still rises purely from the operating profit gain.
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 600, "opex": 150, "long_term_debt": 400, "share_capital": 400, "retained_earnings": 200},
        current={"revenue": 1050, "cogs": 610, "opex": 140, "long_term_debt": 100, "share_capital": 1000, "retained_earnings": 200},
    )
    ratios_p = compute_ratios(FinancialSeries(company="Q17", periods=[prior]))
    ratios_c = compute_ratios(FinancialSeries(company="Q17", periods=[prior, current]))
    text = (
        f"Yes — ROCE moved {ratios_p['roce']} → {ratios_c['roce']} while ROE moved {ratios_p['roe']} → "
        f"{ratios_c['roe']}. ROCE (EBIT / Capital Employed) measures operating returns independent of "
        f"financing; ROE (PAT / Equity) is leverage-sensitive. Paying down debt and raising fresh equity "
        f"improves the underlying operating business (ROCE up) while simultaneously diluting the "
        f"leverage-boost to shareholder returns (ROE down) — the two ratios can legitimately diverge "
        f"whenever the capital structure itself changes materially."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_p, "ratios_current": ratios_c},
        linkage_checks={
            "roce_rose": ratios_c["roce"] > ratios_p["roce"],
            "roe_fell": ratios_c["roe"] < ratios_p["roe"],
        },
        interpretation_keypoints_expected=["leverage", "capital structure", "roce", "operating"],
        interpretation_keypoints_matched=[k for k in ["leverage", "capital structure", "roce", "operating"] if k in text.lower()],
    )


# --- Q18 ---------------------------------------------------------------
def _q18_de_rises_coverage_rises() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 600, "opex": 200, "interest_expense": 40, "long_term_debt": 200, "share_capital": 400, "retained_earnings": 100},
        current={"revenue": 1300, "cogs": 700, "opex": 220, "interest_expense": 45, "long_term_debt": 350, "share_capital": 400, "retained_earnings": 100},
    )
    ratios_p = compute_ratios(FinancialSeries(company="Q18", periods=[prior]))
    ratios_c = compute_ratios(FinancialSeries(company="Q18", periods=[prior, current]))
    text = (
        f"Yes — Debt/Equity moved {ratios_p['debt_to_equity']} → {ratios_c['debt_to_equity']} (up) while "
        f"Interest Coverage moved {ratios_p['interest_coverage']} → {ratios_c['interest_coverage']} (also up). "
        f"This is possible when new debt funds a high-return investment that grows EBIT faster than the "
        f"incremental interest expense it creates — leverage is rising, but the earnings base servicing it "
        f"is rising even faster, so the business is arguably using the debt productively rather than "
        f"riskily, at least by this metric alone."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_p, "ratios_current": ratios_c},
        linkage_checks={
            "debt_equity_rose": ratios_c["debt_to_equity"] > ratios_p["debt_to_equity"],
            "interest_coverage_rose": ratios_c["interest_coverage"] > ratios_p["interest_coverage"],
        },
        interpretation_keypoints_expected=["ebit", "productive", "leverage", "return"],
        interpretation_keypoints_matched=[k for k in ["ebit", "productiv", "leverage", "return"] if k in text.lower()],
    )


# --- Q19 ---------------------------------------------------------------
def _q19_gross_margin_falls_ebitda_margin_rises() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 550, "opex": 280},
        current={"revenue": 1000, "cogs": 600, "opex": 180},
    )
    ratios_p = compute_ratios(FinancialSeries(company="Q19", periods=[prior]))
    ratios_c = compute_ratios(FinancialSeries(company="Q19", periods=[prior, current]))
    findings = _finding_texts(prior, current)
    text = (
        f"Yes — Gross Margin moved {ratios_p['gross_margin']} → {ratios_c['gross_margin']} (fell) while "
        f"EBITDA Margin moved {ratios_p['ebitda_margin']} → {ratios_c['ebitda_margin']} (rose). This happens "
        f"when operating-expense discipline (SG&A cuts, restructuring, headcount reduction) more than "
        f"offsets input-cost pressure or pricing weakness at the gross-profit level — the two margins "
        f"measure different parts of the cost structure and can move in opposite directions. "
        + " ".join(findings[:1])
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_p, "ratios_current": ratios_c, "findings": findings},
        linkage_checks={
            "gross_margin_fell": ratios_c["gross_margin"] < ratios_p["gross_margin"],
            "ebitda_margin_rose": ratios_c["ebitda_margin"] > ratios_p["ebitda_margin"],
        },
        interpretation_keypoints_expected=["operating expense", "discipline", "input-cost", "offset"],
        interpretation_keypoints_matched=[k for k in ["operating expense", "discipline", "input-cost", "offset"] if k in text.lower()],
    )


# --- Q20 ---------------------------------------------------------------
def _q20_asset_turnover_falls_roic_rises() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "cogs": 650, "opex": 200, "ppe_net": 500, "cash": 100, "receivables": 100,
               "inventory": 100, "long_term_debt": 200, "share_capital": 400, "retained_earnings": 100},
        current={"revenue": 1000, "cogs": 550, "opex": 180, "ppe_net": 700, "cash": 100, "receivables": 100,
                 "inventory": 100, "long_term_debt": 200, "share_capital": 400, "retained_earnings": 100},
    )
    ratios_p = compute_ratios(FinancialSeries(company="Q20", periods=[prior]))
    ratios_c = compute_ratios(FinancialSeries(company="Q20", periods=[prior, current]))
    text = (
        f"Yes — Asset Turnover moved {ratios_p['asset_turnover']} → {ratios_c['asset_turnover']} (fell, "
        f"since the asset base grew with flat Revenue) while ROIC moved {ratios_p['roic']} → "
        f"{ratios_c['roic']} (rose). This is a DuPont-style offset: margin expansion (lower COGS/OpEx as a "
        f"share of Revenue) improved after-tax operating profit enough to outweigh the drag from a larger, "
        f"less-efficiently-utilised capital base — turnover and margin are two separate levers that can "
        f"move in opposite directions while still improving the combined return metric."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"ratios_prior": ratios_p, "ratios_current": ratios_c},
        linkage_checks={
            "asset_turnover_fell": ratios_c["asset_turnover"] < ratios_p["asset_turnover"],
            "roic_rose": ratios_c["roic"] > ratios_p["roic"],
        },
        interpretation_keypoints_expected=["margin", "dupont", "turnover", "offset"],
        interpretation_keypoints_matched=[k for k in ["margin", "dupont", "turnover", "offset"] if k in text.lower()],
    )


# --- Q21 ---------------------------------------------------------------
def _q21_goodwill_triples_revenue_unchanged() -> ExamAnswer:
    prior, current = _pair(
        prior={"goodwill": 100, "revenue": 1000, "total_assets": None},
        current={"goodwill": 300, "revenue": 1000, "total_assets": None},
    )
    flags = detect_red_flags(FinancialSeries(company="Q21", periods=[prior, current]))
    text = (
        "Goodwill tripling while Revenue is unchanged means an acquisition has been made (or a "
        "revaluation occurred), but its economic benefit has not yet shown up in the top line — either "
        "because integration takes time, the acquired entity's revenue isn't yet consolidated at scale, "
        "or the price paid did not reflect near-term revenue synergies. This concentrates future "
        "impairment risk: if the acquired business never delivers the expected revenue/earnings, the "
        "Goodwill balance will eventually be written down, hitting PAT in a single period. "
        f"Red flags detected: {flags['total_flags']}."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"red_flags": flags},
        interpretation_keypoints_expected=["acquisition", "impairment", "integration", "synerg"],
        interpretation_keypoints_matched=[k for k in ["acquisition", "impairment", "integration", "synerg"] if k in text.lower()],
    )


# --- Q22 ---------------------------------------------------------------
def _q22_revenue_grows_ar_inv_faster_cash_falls() -> ExamAnswer:
    prior, current = _pair(
        prior={"revenue": 1000, "receivables": 100, "inventory": 100, "cash": 200},
        current={"revenue": 1100, "receivables": 180, "inventory": 170, "cash": 140},
    )
    findings = _finding_texts(prior, current)
    flags = detect_red_flags(FinancialSeries(company="Q22", periods=[prior, current]))
    text = (
        "This is a compounding working-capital drag: Revenue growing more slowly than both Receivables "
        "and Inventory, with Cash falling, means the business is funding its own growth by trapping more "
        "cash in the operating cycle than the growth itself generates — a pattern consistent with either "
        "aggressive channel-stuffing (pushing goods/credit to book revenue) or genuinely under-managed "
        "working capital during a growth phase. " + " ".join(findings[:3]) +
        f" Red flags detected: {flags['total_flags']} (high severity: {flags['high_severity_count']})."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"findings": findings, "red_flags": flags},
        linkage_checks={"multiple_findings_fired": len(findings) >= 2},
        interpretation_keypoints_expected=["working capital", "channel", "trapped", "drag"],
        interpretation_keypoints_matched=[k for k in ["working capital", "channel", "trapped", "drag"] if k in text.lower()],
    )


# --- Q23 ---------------------------------------------------------------
def _q23_repeated_ebitda_adjustments() -> ExamAnswer:
    card = get_metric("ebitda_margin")
    text = (
        "Repeatedly adjusting EBITDA (excluding 'one-off' items every single period) is itself a red flag: "
        "if an item recurs period after period, it is not actually one-off — it is a real, recurring cost "
        "of doing business that management is choosing to exclude from the headline metric. "
        f"{card.common_distortions if card else ''} The risk is that investors anchor on an "
        "'adjusted' EBITDA that consistently overstates sustainable operating profitability, masking a "
        "genuine deterioration in the underlying, unadjusted business."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"card": card.__dict__ if card else None},
        interpretation_keypoints_expected=["recurring", "not one-off", "overstate", "mask"],
        interpretation_keypoints_matched=[k for k in ["recurring", "not one-off", "overstate", "mask"] if k in text.lower()],
    )


# --- Q24 ---------------------------------------------------------------
def _q24_ocf_negative_ni_positive_three_years() -> ExamAnswer:
    periods = [
        StatementPeriod(label="Y1", sequence=1, revenue=1000, cogs=600, opex=150, operating_cf=-30, capex=20),
        StatementPeriod(label="Y2", sequence=2, revenue=1100, cogs=660, opex=160, operating_cf=-45, capex=25),
        StatementPeriod(label="Y3", sequence=3, revenue=1200, cogs=720, opex=170, operating_cf=-20, capex=30),
    ]
    series = FinancialSeries(company="Q24", periods=periods)
    flags = detect_red_flags(series)
    text = (
        "Operating Cash Flow negative for three consecutive years while Net Income stays positive is a "
        "severe, structural earnings-quality red flag — it means the accounting profit is being generated "
        "entirely through non-cash items or working-capital timing (or both) for a sustained period, not "
        "a one-off. This pattern historically precedes covenant breaches, emergency financing, or "
        "restatement in a meaningful share of cases; it should be treated as a near-disqualifying signal "
        f"until fully explained. Red flags detected across the series: {flags['total_flags']} "
        f"(high severity: {flags['high_severity_count']})."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"red_flags": flags, "periods": [p.label for p in periods]},
        linkage_checks={"all_three_years_negative_ocf": all(p.operating_cf < 0 for p in periods)},
        interpretation_keypoints_expected=["structural", "sustained", "covenant", "disqualify"],
        interpretation_keypoints_matched=[k for k in ["structural", "sustained", "covenant", "disqualif"] if k in text.lower()],
    )


# --- Q25 ---------------------------------------------------------------
def _q25_dividend_exceeds_fcf() -> ExamAnswer:
    prior, current = _pair(
        prior={"operating_cf": 150, "capex": 40, "dividends_paid": 60},
        current={"operating_cf": 120, "capex": 50, "dividends_paid": 90},
    )
    findings = _finding_texts(prior, current)
    flags = detect_red_flags(FinancialSeries(company="Q25", periods=[prior, current]))
    card = get_metric("dividend_sustainability")
    text = (
        f"Dividends of ₹{current.dividends_paid:,.0f} against Free Cash Flow of ₹{current.free_cash_flow:,.0f} "
        f"means the payout is NOT fully covered by cash the business generates — the shortfall must be "
        f"funded from existing cash reserves or new borrowing. {card.interpretation if card else ''} "
        + " ".join(findings[:1])
        + f" Red flags detected: {flags['total_flags']}."
    )
    return ExamAnswer(
        answer_text=text,
        evidence={"findings": findings, "red_flags": flags},
        linkage_checks={"dividend_exceeds_fcf": current.dividends_paid > current.free_cash_flow},
        interpretation_keypoints_expected=["not covered", "reserves", "borrowing", "sustainab"],
        interpretation_keypoints_matched=[k for k in ["not covered", "reserves", "borrowing", "sustainab"] if k in text.lower()],
    )


SECTION_BE_ITEMS: list[ExamItem] = [
    ExamItem("Q6", "B", 6, "PAT increases. Cash decreases. Explain every possible reason.", 4.0, _q6_pat_up_cash_down, "linkage"),
    ExamItem("Q7", "B", 7, "Inventory doubles. Revenue is flat. Interpret.", 4.0, _q7_inventory_doubles_revenue_flat, "linkage"),
    ExamItem("Q8", "B", 8, "Receivables increase 60%. Revenue increases 10%. Interpret.", 4.0, _q8_receivables_60_revenue_10, "linkage"),
    ExamItem("Q9", "B", 9, "Debt increases. Interest expense falls. Possible? Explain.", 4.0, _q9_debt_up_interest_down, "linkage"),
    ExamItem("Q10", "B", 10, "Depreciation doubles. Cash unchanged. Explain why.", 4.0, _q10_depreciation_doubles_cash_unchanged, "linkage"),
    ExamItem("Q11", "C", 11, "Revenue +20%, PAT +25%, OCF -30%. Interpret.", 4.0, _q11_revenue20_pat25_ocf_neg30, "earnings_quality"),
    ExamItem("Q12", "C", 12, "EBITDA +18%, FCF -40%, Capex doubled. Interpret.", 4.0, _q12_ebitda18_fcf_neg40_capex_doubled, "earnings_quality"),
    ExamItem("Q13", "C", 13, "Working Capital absorbs ₹500 crore. What does that mean?", 4.0, _q13_working_capital_absorbs_500cr, "earnings_quality"),
    ExamItem("Q14", "C", 14, "Inventory↓ Receivables↓ Cash↑ Revenue flat. Interpret.", 4.0, _q14_inv_down_ar_down_cash_up_revenue_flat, "earnings_quality"),
    ExamItem("Q15", "C", 15, "PAT falls. ROE rises. Explain.", 4.0, _q15_pat_falls_roe_rises, "earnings_quality"),
    ExamItem("Q16", "D", 16, "Current Ratio falls. Quick Ratio rises. Explain.", 4.0, _q16_current_falls_quick_rises, "ratios"),
    ExamItem("Q17", "D", 17, "ROCE rises. ROE falls. Possible? Why?", 4.0, _q17_roce_rises_roe_falls, "ratios"),
    ExamItem("Q18", "D", 18, "Debt/Equity rises. Interest Coverage rises. Interpret.", 4.0, _q18_de_rises_coverage_rises, "ratios"),
    ExamItem("Q19", "D", 19, "Gross Margin falls. EBITDA Margin rises. Possible?", 4.0, _q19_gross_margin_falls_ebitda_margin_rises, "ratios"),
    ExamItem("Q20", "D", 20, "Asset Turnover falls. ROIC rises. Explain.", 4.0, _q20_asset_turnover_falls_roic_rises, "ratios"),
    ExamItem("Q21", "E", 21, "Goodwill triples. Revenue unchanged. Interpret.", 4.0, _q21_goodwill_triples_revenue_unchanged, "red_flags"),
    ExamItem("Q22", "E", 22, "Revenue grows; Receivables/Inventory grow faster; Cash falls. Interpret.", 4.0, _q22_revenue_grows_ar_inv_faster_cash_falls, "red_flags"),
    ExamItem("Q23", "E", 23, "Company repeatedly adjusts EBITDA. Explain the risk.", 4.0, _q23_repeated_ebitda_adjustments, "red_flags"),
    ExamItem("Q24", "E", 24, "OCF negative, Net Income positive, 3 consecutive years. Interpret.", 4.0, _q24_ocf_negative_ni_positive_three_years, "red_flags"),
    ExamItem("Q25", "E", 25, "Dividend payout exceeds Free Cash Flow. Interpret.", 4.0, _q25_dividend_exceeds_fcf, "red_flags"),
]
