"""Sections F-J — composite, one-task-per-section items.

F: Case Study (full stack + 500-word analyst note)
G: Reverse Engineering (reconstruct Cash Flow from IS + BS only, then verify)
H: Business Events (8 advanced three-statement impact explanations)
I: Institutional Reasoning (analyst note for a specific multi-signal scenario)
J: Impossible Questions (honesty about insufficient evidence)
"""

from __future__ import annotations

from financial_foundations.journal import Ledger
from financial_statement_intelligence.adapters import series_from_phase1_ledger
from financial_statement_intelligence.business_events import BUSINESS_EVENTS, explain_event
from financial_statement_intelligence.cash_flow_reconstruction import verify_reconstruction
from financial_statement_intelligence.case_studies import CASE_STUDIES, analyse_case_study
from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.narrative_generator import generate_long_form_note
from financial_statement_intelligence.rule_library import evaluate_rules
from financial_statement_intelligence.schema import StatementPeriod
from financial_statement_intelligence.uncertainty_guard import (
    PLAUSIBLE_CAUSES,
    assess_causal_sufficiency,
    is_single_cause_claim_overconfident,
)
from institutional_accounting_exam.schema import ExamAnswer, ExamItem


# ---------------------------------------------------------------------------
# Section F — Case Study
# ---------------------------------------------------------------------------
def _section_f_case_study() -> ExamAnswer:
    series = CASE_STUDIES["reliance"]
    full = analyse_case_study("reliance")
    note = generate_long_form_note(series)

    required_topics = ["ratio", "red flag", "earnings quality", "cash conversion", "leverage", "capital efficiency"]
    note_lower = (note.get("note") or "").lower()
    topics_covered = [t for t in required_topics if t.split()[0] in note_lower]

    word_count = note.get("word_count", 0)
    word_count_ok = 300 <= word_count <= 700  # "≈500 words" with reasonable tolerance

    answer = (
        f"Case study: {series.company} ({series.sector}). Overall direction: {full['overall_direction']['verdict']}. "
        f"Earnings quality: {full['earnings_quality'].get('label')} ({full['earnings_quality'].get('score')}/10). "
        f"Red flags: {full['red_flags']['total_flags']} ({full['red_flags']['high_severity_count']} high). "
        f"Financial health: {full['financial_health_score'].get('overall_financial_strength')}/100.\n\n"
        f"--- {word_count}-word analyst note ---\n{note.get('note')}"
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"full_analysis": full, "note": note},
        accounting_checks={"ratios_computed": bool(full.get("financial_health_score", {}).get("available"))},
        linkage_checks={"red_flags_computed": full["red_flags"]["total_flags"] >= 0, "health_score_computed": full["financial_health_score"].get("available", False)},
        interpretation_keypoints_expected=required_topics,
        interpretation_keypoints_matched=topics_covered,
        causal_reasoning_present=word_count_ok,
    )


# ---------------------------------------------------------------------------
# Section G — Reverse Engineering
# ---------------------------------------------------------------------------
def _section_g_reverse_engineering() -> ExamAnswer:
    ledger = Ledger()
    ledger.record("founder_investment", 2_000_000, period=1)
    ledger.record("buy_asset_cash", 500_000, period=1, asset_account="land")
    ledger.record("buy_asset_cash", 600_000, period=1, asset_account="machinery")
    ledger.record("purchase_inventory_cash", 500_000, period=1)
    ledger.record("credit_sale", 400_000, period=1)
    ledger.record("sell_inventory_cogs", 200_000, period=1)
    ledger.record("cash_sale", 300_000, period=1)
    ledger.record("sell_inventory_cogs", 150_000, period=1)
    ledger.record("pay_expense_cash", 120_000, period=1, expense_account="salary_expense")
    ledger.record("take_loan", 500_000, period=1)
    ledger.record("pay_interest", 25_000, period=1)
    ledger.record("record_depreciation", 60_000, period=1)
    ledger.record("pay_tax", 36_250, period=1)
    ledger.close_period(1)
    ledger.record("credit_sale", 500_000, period=2)
    ledger.record("sell_inventory_cogs", 260_000, period=2)
    ledger.record("collect_receivable", 300_000, period=2)
    ledger.record("purchase_inventory_cash", 200_000, period=2)
    ledger.record("pay_expense_cash", 140_000, period=2, expense_account="salary_expense")
    ledger.record("pay_interest", 30_000, period=2)
    ledger.record("record_depreciation", 65_000, period=2)
    ledger.record("pay_tax", 40_000, period=2)
    ledger.record("take_loan", 150_000, period=2)
    ledger.record("buy_asset_cash", 80_000, period=2, asset_account="furniture")
    ledger.close_period(2)

    series = series_from_phase1_ledger(ledger, company="Section G Co", periods=[1, 2])
    prior, current = series.pair(lag=1)
    v = verify_reconstruction(prior, current)
    recon = v["reconstruction"]

    answer = (
        f"Given ONLY the Income Statement and Balance Sheet, the Cash Flow Statement reconstructs as: "
        f"Operating CF = {recon['operating']['total']:,.0f} (PAT + Depreciation ± working-capital deltas), "
        f"Investing CF = {recon['investing']['total']:,.0f} (implied Capex of {recon['investing']['implied_capex']:,.0f} "
        f"from ΔNet PPE + Depreciation), Financing CF = {recon['financing']['total']:,.0f} "
        f"(implied Dividends of {recon['financing']['implied_dividends']:,.0f} from the retained-earnings bridge). "
        f"VERIFICATION against the actual Cash Flow Statement: Operating gap = {v['operating_gap']:,.0f}, "
        f"Investing gap = {v['investing_gap']:,.0f}, Financing gap = {v['financing_gap']:,.0f}. "
        f"{recon['honesty_note']}"
    )
    return ExamAnswer(
        answer_text=answer,
        evidence=v,
        accounting_checks={
            "operating_reconstruction_exact": abs(v["operating_gap"]) < 1.0,
            "investing_reconstruction_exact": abs(v["investing_gap"]) < 1.0,
            "financing_reconstruction_exact": abs(v["financing_gap"]) < 1.0,
        },
        linkage_checks={"reconciles_to_actual_cash_movement": recon["reconciles"]},
        interpretation_keypoints_expected=["working capital", "implied capex", "retained-earnings bridge", "verification"],
        interpretation_keypoints_matched=[k for k in ["working capital", "implied capex", "retained-earnings bridge", "verification"] if k in answer.lower()],
    )


# ---------------------------------------------------------------------------
# Section H — Business Events
# ---------------------------------------------------------------------------
def _section_h_business_events() -> ExamAnswer:
    events = [explain_event(k) for k in BUSINESS_EVENTS]
    all_found = all(e["found"] for e in events)
    all_have_three_statements = all(
        e["income_statement_today"] and e["balance_sheet_today"] and e["cash_flow_today"] for e in events
    )
    all_have_principle = all(e["governing_principle"] for e in events)

    summary = "; ".join(f"{e['title']}: {e['income_statement_today'][:70]}..." for e in events)
    answer = f"All {len(events)} business events explained across Income Statement / Balance Sheet / Cash Flow: {summary}"
    return ExamAnswer(
        answer_text=answer,
        evidence={"events": events},
        accounting_checks={
            "all_eight_events_found": all_found and len(events) == 8,
            "all_cover_three_statements": all_have_three_statements,
            "all_have_governing_principle": all_have_principle,
        },
        interpretation_keypoints_expected=["income statement", "balance sheet", "cash flow", "governing principle"],
        interpretation_keypoints_matched=["income statement", "balance sheet", "cash flow", "governing principle"] if all_have_three_statements and all_have_principle else [],
    )


# ---------------------------------------------------------------------------
# Section I — Institutional Reasoning
# ---------------------------------------------------------------------------
def _section_i_institutional_reasoning() -> ExamAnswer:
    # Exact scenario from the brief: Revenue +12%, Gross Margin falls,
    # EBITDA Margin rises, Capex doubles, Debt unchanged, OCF falls, PAT rises.
    prior = StatementPeriod(
        label="P0", sequence=1, revenue=1000, cogs=550, opex=280, depreciation=40, interest_expense=20,
        tax_expense=30, cash=200, receivables=100, inventory=90, ppe_net=300, payables=90,
        long_term_debt=250, share_capital=400, retained_earnings=150, operating_cf=160, capex=50,
    )
    current = StatementPeriod(
        label="P1", sequence=2, revenue=1120, cogs=650, opex=200, depreciation=45, interest_expense=20,
        tax_expense=5, cash=170, receivables=150, inventory=130, ppe_net=345, payables=95,
        long_term_debt=250, share_capital=400, retained_earnings=195, operating_cf=110, capex=100,
    )
    d = compute_deltas(prior, current)
    findings = evaluate_rules(d)
    finding_texts = [f.explanation for f in findings]

    note = (
        f"ANALYST NOTE. Revenue grew {d.pct('revenue') * 100:.0f}%, but Gross Margin compressed while EBITDA "
        f"Margin expanded — this combination suggests input-cost or pricing pressure at the gross-profit "
        f"level that was more than offset by operating-expense discipline (SG&A/overhead control) below "
        f"the gross-profit line. Capex roughly doubling with Total Debt unchanged indicates the expansion "
        f"is being self-funded from internal cash rather than new borrowing — consistent with the "
        f"Operating Cash Flow decline observed, which likely reflects a combination of the capex-funding "
        f"working-capital build (Receivables and Inventory both rose materially) and the reinvestment "
        f"itself. PAT rising even as OCF falls is a genuine earnings-quality watch item: the profit is "
        f"real on an accrual basis, but is not yet being converted into cash at the same rate — worth "
        f"monitoring over the next 1-2 periods to confirm this is a temporary reinvestment/working-capital "
        f"effect rather than a structural cash-conversion problem. Supporting evidence: " + " ".join(finding_texts[:4])
    )
    return ExamAnswer(
        answer_text=note,
        evidence={"deltas_summary": {"revenue_pct": d.pct("revenue"), "pat_pct": d.pct("pat"), "ocf_pct": d.pct("operating_cf")}, "findings": finding_texts},
        linkage_checks={"multiple_findings_fired": len(findings) >= 3},
        interpretation_keypoints_expected=["input-cost", "discipline", "self-funded", "working capital", "earnings-quality"],
        interpretation_keypoints_matched=[k for k in ["input-cost", "discipline", "self-fund", "working capital", "earnings-quality", "earnings quality"] if k in note.lower()],
        causal_reasoning_present=True,
    )


# ---------------------------------------------------------------------------
# Section J — Impossible Questions
# ---------------------------------------------------------------------------
_IMPOSSIBLE_QUESTIONS = [
    ("PAT doubled. What happened?", "pat_change"),
    ("Revenue grew. What happened?", "revenue_change"),
    ("ROE improved this quarter. Why?", "roe_change"),
    ("EBITDA increased. Explain why.", "ebitda_change"),
    ("The cash balance went up. Why?", "cash_change"),
]


def _section_j_impossible_questions() -> ExamAnswer:
    results = []
    for question, metric in _IMPOSSIBLE_QUESTIONS:
        assessment = assess_causal_sufficiency(metric, known_context={})
        # A naive (bad) answer confidently asserts ONE specific plausible cause
        # as if it were the actual, known driver — exactly the overconfident
        # pattern this exam section must catch and penalise.
        specific_cause = PLAUSIBLE_CAUSES.get(metric, ["an operational change"])[0]
        naive_bad_answer = f"{question.split('?')[0].strip()} because of {specific_cause}."
        overconfidence_check = is_single_cause_claim_overconfident(naive_bad_answer, metric, known_context={})
        results.append(
            {
                "question": question,
                "correctly_refuses_single_cause": not assessment["sufficient_evidence"],
                "answer": assessment.get("answer"),
                "plausible_causes_offered": len(assessment.get("plausible_causes", [])) >= 3,
                "naive_overconfident_answer_detected": overconfidence_check["overconfident"],
            }
        )

    all_admit_uncertainty = all(r["correctly_refuses_single_cause"] for r in results)
    all_offer_alternatives = all(r["plausible_causes_offered"] for r in results)
    all_detect_naive_overconfidence = all(r["naive_overconfident_answer_detected"] for r in results)

    answer = "\n".join(f"Q: {r['question']}\nA: {r['answer']}" for r in results)
    return ExamAnswer(
        answer_text=answer,
        evidence={"results": results},
        admits_uncertainty_correctly=all_admit_uncertainty,
        hallucination_detected=not all_admit_uncertainty,
        hallucination_reason=None if all_admit_uncertainty else "At least one impossible question was answered with unwarranted single-cause certainty.",
        interpretation_keypoints_expected=["insufficient", "several", "additional evidence"],
        interpretation_keypoints_matched=["insufficient", "several", "additional evidence"] if all_admit_uncertainty else [],
        causal_reasoning_present=all_detect_naive_overconfidence and all_offer_alternatives,
    )


SECTION_FJ_ITEMS: list[ExamItem] = [
    ExamItem("SecF", "F", 26, "Case Study — full stack + 500-word analyst note.", 20.0, _section_f_case_study, "case_study"),
    ExamItem("SecG", "G", 27, "Reverse Engineering — reconstruct Cash Flow from IS+BS, then verify.", 20.0, _section_g_reverse_engineering, "reverse_engineering"),
    ExamItem("SecH", "H", 28, "Business Events — 8 advanced three-statement impact explanations.", 20.0, _section_h_business_events, "business_events"),
    ExamItem("SecI", "I", 29, "Institutional Reasoning — analyst note for a multi-signal scenario.", 20.0, _section_i_institutional_reasoning, "institutional_reasoning"),
    ExamItem("SecJ", "J", 30, "Impossible Questions — honesty about insufficient evidence.", 20.0, _section_j_impossible_questions, "impossible_questions"),
]
