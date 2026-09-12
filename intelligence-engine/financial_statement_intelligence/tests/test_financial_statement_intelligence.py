"""Phase 2 — Financial Statement Intelligence acceptance tests.

Validates every success criterion from the brief:

1. Explain the financial condition of a company from its statements.
2. Connect changes across Income Statement, Balance Sheet, Cash Flow.
3. Identify strengths, weaknesses, and red flags with supporting evidence.
4. Generate analyst-quality narratives instead of listing metrics.
5. Distinguish between accounting performance and economic performance
   (PAT vs cash, ROE vs PAT decomposition, etc.).
6. Explain WHY a metric changed, not just what changed.
"""

from __future__ import annotations

import pytest

from financial_statement_intelligence import production
from financial_statement_intelligence.adapters import statement_period_from_phase1
from financial_statement_intelligence.case_studies import CASE_STUDIES, analyse_case_study, list_case_studies
from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.earnings_quality import assess_earnings_quality
from financial_statement_intelligence.health_score import score_financial_health
from financial_statement_intelligence.industry_lens import industry_context, list_sectors
from financial_statement_intelligence.metric_concepts import all_metrics, get_metric
from financial_statement_intelligence.narrative_generator import generate_narrative
from financial_statement_intelligence.ratio_engine import compute_ratios, growth_metrics, ratio_trends
from financial_statement_intelligence.red_flag_detector import detect_red_flags
from financial_statement_intelligence.rule_library import COMPARISON_PAIRS, rule_library, evaluate_rules
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod
from financial_statement_intelligence.statement_intelligence import (
    interpret_period,
    overall_direction,
    trend_windows,
)

# ---------------------------------------------------------------------------
# Shared fixtures: a clean "improving" company and a "PAT up, OCF down" company
# ---------------------------------------------------------------------------
def _improving_series() -> FinancialSeries:
    periods = [
        StatementPeriod(label="FY22", sequence=1, revenue=900, cogs=550, opex=180, depreciation=40,
                         interest_expense=25, tax_expense=20, cash=120, receivables=80, inventory=60,
                         ppe_net=250, payables=70, long_term_debt=200, share_capital=400, retained_earnings=60,
                         operating_cf=100, capex=40, dividends_paid=8),
        StatementPeriod(label="FY23", sequence=2, revenue=1000, cogs=580, opex=190, depreciation=42,
                         interest_expense=22, tax_expense=28, cash=160, receivables=85, inventory=62,
                         ppe_net=260, payables=78, long_term_debt=170, share_capital=400, retained_earnings=105,
                         operating_cf=140, capex=45, dividends_paid=10),
        StatementPeriod(label="FY24", sequence=3, revenue=1150, cogs=650, opex=205, depreciation=45,
                         interest_expense=18, tax_expense=38, cash=210, receivables=88, inventory=64,
                         ppe_net=270, payables=85, long_term_debt=140, share_capital=400, retained_earnings=160,
                         operating_cf=175, capex=48, dividends_paid=12),
    ]
    return FinancialSeries(company="Improving Co", periods=periods, sector="it_services")


def _pat_up_ocf_down_series() -> FinancialSeries:
    periods = [
        StatementPeriod(label="FY23", sequence=1, revenue=1000, cogs=600, opex=200, depreciation=50,
                         interest_expense=20, tax_expense=20, cash=150, receivables=100, inventory=80,
                         ppe_net=300, payables=90, long_term_debt=200, share_capital=500, retained_earnings=100,
                         operating_cf=120, capex=60, dividends_paid=10),
        StatementPeriod(label="FY24", sequence=2, revenue=1150, cogs=750, opex=230, depreciation=55,
                         interest_expense=30, tax_expense=15, cash=100, receivables=180, inventory=110,
                         ppe_net=340, payables=95, long_term_debt=260, share_capital=500, retained_earnings=140,
                         operating_cf=90, capex=90, dividends_paid=12),
    ]
    return FinancialSeries(company="Deteriorating Co", periods=periods, sector="retail")


# ---------------------------------------------------------------------------
# Success criterion 1 — explain the financial condition of a company
# ---------------------------------------------------------------------------
def test_overall_direction_improving():
    result = overall_direction(_improving_series())
    assert result["verdict"] == "improving"
    assert result["net_score"] > 0
    assert result["evidence"]


def test_overall_direction_deteriorating_or_mixed():
    result = overall_direction(_pat_up_ocf_down_series())
    assert result["verdict"] in ("deteriorating", "mixed")


def test_production_analyze_returns_full_picture():
    out = production.analyze(_improving_series())
    for key in (
        "overall_direction", "statement_interpretation", "trend_analysis",
        "ratios_latest", "growth", "earnings_quality", "red_flags",
        "financial_health_score", "narrative", "industry_context",
    ):
        assert key in out, key


# ---------------------------------------------------------------------------
# Success criterion 2 — connect changes across IS / BS / CF
# ---------------------------------------------------------------------------
def test_deltas_span_all_three_statements():
    series = _pat_up_ocf_down_series()
    prior, current = series.pair(lag=1)
    d = compute_deltas(prior, current)
    # Income Statement
    assert d.pct("revenue") is not None
    assert d.pct("pat") is not None
    # Balance Sheet
    assert d.pct("receivables") is not None
    assert d.pct("total_debt") is not None
    # Cash Flow
    assert d.pct("operating_cf") is not None
    assert d.get("free_cash_flow") is not None


def test_pat_up_receivables_up_cash_flow_down_chain_detected():
    """Module 4's literal example chain: Revenue↑ → Receivables↑ → OCF↓ → WC↑ → FCF↓."""
    series = _pat_up_ocf_down_series()
    prior, current = series.pair(lag=1)
    d = compute_deltas(prior, current)
    findings = evaluate_rules(d)
    rule_ids = {f.rule_id for f in findings}
    assert "revenue_vs_receivables__b_faster" in rule_ids
    assert "pat_vs_operating_cf__both_down" in rule_ids or "pat_vs_operating_cf__a_up_b_down" in rule_ids
    assert d.get("free_cash_flow").current < d.get("free_cash_flow").prior


def test_interpret_period_returns_findings_with_evidence():
    pi = interpret_period(_improving_series(), index=-1)
    assert pi.findings
    for f in pi.findings:
        assert f.evidence  # every finding must carry evidence, never a bare claim


# ---------------------------------------------------------------------------
# Success criterion 3 — identify strengths, weaknesses, red flags with evidence
# ---------------------------------------------------------------------------
def test_red_flags_detected_for_deteriorating_company():
    flags = detect_red_flags(_pat_up_ocf_down_series())
    assert flags["total_flags"] > 0
    for row in flags["flags"]:
        assert row["risk"]
        assert row["evidence"]
        assert 0 <= row["confidence"] <= 1
        assert row["severity"] in ("low", "medium", "high")


def test_red_flags_minimal_for_improving_company():
    improving = detect_red_flags(_improving_series())
    deteriorating = detect_red_flags(_pat_up_ocf_down_series())
    assert improving["high_severity_count"] <= deteriorating["high_severity_count"]


def test_repeated_equity_dilution_detected():
    periods = [
        StatementPeriod(label="FY22", sequence=1, revenue=500, cogs=300, opex=100, share_capital=100,
                         cash=50, operating_cf=40, capex=10),
        StatementPeriod(label="FY23", sequence=2, revenue=520, cogs=310, opex=105, share_capital=115,
                         cash=55, operating_cf=42, capex=10),
        StatementPeriod(label="FY24", sequence=3, revenue=540, cogs=320, opex=108, share_capital=135,
                         cash=60, operating_cf=44, capex=10),
    ]
    series = FinancialSeries(company="Diluting Co", periods=periods)
    flags = detect_red_flags(series)
    risks = {f["risk"] for f in flags["flags"]}
    assert "repeated equity dilution" in risks


def test_sustained_negative_fcf_detected():
    periods = [
        StatementPeriod(label="FY22", sequence=1, revenue=500, cogs=300, opex=100, operating_cf=20, capex=80),
        StatementPeriod(label="FY23", sequence=2, revenue=520, cogs=310, opex=105, operating_cf=15, capex=90),
        StatementPeriod(label="FY24", sequence=3, revenue=540, cogs=320, opex=108, operating_cf=25, capex=100),
    ]
    series = FinancialSeries(company="Cash Burner", periods=periods)
    flags = detect_red_flags(series)
    risks = {f["risk"] for f in flags["flags"]}
    assert "sustained negative free cash flow" in risks


# ---------------------------------------------------------------------------
# Success criterion 4 — analyst-quality narrative, not a metric list
# ---------------------------------------------------------------------------
def test_narrative_is_grounded_prose_not_a_metric_dump():
    n = generate_narrative(_improving_series())
    assert n["available"] is True
    assert len(n["narrative"]) > 60
    assert n["sentence_count"] >= 2
    assert n["evidence"]
    # It should read like prose (contains connecting words), not "Revenue: 100. EBITDA: 50."
    assert ":" not in n["narrative"].split(".")[0]


def test_narrative_matches_flat_revenue_margin_expansion_example():
    """The brief's own example: flat revenue + margin expansion = pricing power."""
    n = generate_narrative(CASE_STUDIES["asian_paints"])
    assert "pricing power" in n["narrative"].lower() or "margin" in n["narrative"].lower()


def test_narrative_never_invents_unsupplied_drivers():
    n = generate_narrative(_improving_series())
    assert "driven primarily by" not in n["narrative"]  # no driver hints were supplied


def test_narrative_uses_driver_hints_when_supplied():
    n = generate_narrative(_improving_series(), drivers={"pricing_growth": 0.06, "volume_growth": 0.09})
    assert "driven primarily by" in n["narrative"]
    assert "realisation" in n["narrative"] or "volume" in n["narrative"]


# ---------------------------------------------------------------------------
# Success criterion 5 — accounting performance vs economic performance
# ---------------------------------------------------------------------------
def test_earnings_quality_distinguishes_accounting_from_cash():
    good = assess_earnings_quality(_improving_series())
    bad = assess_earnings_quality(_pat_up_ocf_down_series())
    assert good["available"] and bad["available"]
    assert good["score"] > bad["score"]
    assert bad["label"].lower().startswith("low") or bad["score"] < 8


def test_roe_vs_pat_decomposition_question():
    """Module 15's 'Why did ROE improve despite lower net income?' — must be
    answerable causally, not just descriptively."""
    periods = [
        StatementPeriod(label="FY23", sequence=1, revenue=1000, cogs=600, opex=150, pat=150,
                         share_capital=300, retained_earnings=200, treasury_stock=0, cash=50,
                         operating_cf=140, capex=20),
        StatementPeriod(label="FY24", sequence=2, revenue=1000, cogs=620, opex=160, pat=120,
                         share_capital=300, retained_earnings=100, treasury_stock=150, cash=40,
                         operating_cf=110, capex=20, buybacks=250),
    ]
    series = FinancialSeries(company="Buyback Co", periods=periods)
    ratios = compute_ratios(series)
    prior_ratios = compute_ratios(series, period_index=0)
    # ROE should rise even though PAT fell, because Equity shrank faster (buybacks).
    assert ratios["roe"] > prior_ratios["roe"]
    d = compute_deltas(series.periods[0], series.periods[1])
    findings = evaluate_rules(d)
    roe_finding = next((f for f in findings if f.rule_id.startswith("roe_vs_pat")), None)
    assert roe_finding is not None
    assert "duPont" in roe_finding.explanation or "equity" in roe_finding.explanation.lower()


def test_pat_ne_cash_flow_is_explicit_in_findings():
    series = _pat_up_ocf_down_series()
    prior, current = series.pair(lag=1)
    findings = evaluate_rules(compute_deltas(prior, current))
    assert any("cash" in f.explanation.lower() for f in findings)
    assert current.pat != current.operating_cf  # the accounting/economic divergence is real in the fixture


# ---------------------------------------------------------------------------
# Success criterion 6 — explain WHY a metric changed
# ---------------------------------------------------------------------------
def test_every_metric_concept_has_full_analyst_context():
    for key, card in all_metrics().items():
        assert card.definition, key
        assert card.formula, key
        assert card.drivers, key
        assert card.interpretation, key
        assert card.industry_differences, key
        assert card.common_distortions, key


def test_findings_always_explain_why_not_just_what():
    series = _pat_up_ocf_down_series()
    prior, current = series.pair(lag=1)
    findings = evaluate_rules(compute_deltas(prior, current))
    assert findings
    for f in findings:
        # Every explanation must contain a causal connector, not just numbers.
        assert any(w in f.explanation.lower() for w in ("—", "because", "signal", "suggest", "may", "likely", "risk", "indicate"))


# ---------------------------------------------------------------------------
# Rule library integrity
# ---------------------------------------------------------------------------
def test_rule_library_exceeds_200():
    assert len(rule_library()) >= 200


def test_rule_library_ids_unique():
    ids = [r.rule_id for r in rule_library()]
    assert len(ids) == len(set(ids))


def test_comparison_pairs_direction_sanity():
    """Spot-check a handful of pairs for directional correctness — this is
    the exact bug class found and fixed during development."""
    d = compute_deltas(
        StatementPeriod(label="P0", sequence=1, revenue=1000, receivables=100, cash=200, total_liabilities=None),
        StatementPeriod(label="P1", sequence=2, revenue=1100, receivables=200, cash=150),
    )
    findings = {f.rule_id: f for f in evaluate_rules(d)}
    # Receivables (+100%) far outpaced Revenue (+10%) — must be flagged as risk (b_faster), not praised.
    key = "revenue_vs_receivables__b_faster"
    assert key in findings
    assert "risk" in findings[key].explanation.lower() or "aggressive" in findings[key].explanation.lower()


# ---------------------------------------------------------------------------
# Ratio & trend engine
# ---------------------------------------------------------------------------
def test_ratio_trends_classify_direction():
    trends = ratio_trends(_improving_series())
    by_key = {t.key: t for t in trends}
    assert by_key["current_ratio"].direction in ("improving", "deteriorating", "stable", "insufficient_data")
    assert len(trends) == len(compute_ratios(_improving_series()))


def test_growth_metrics_cagr():
    g = growth_metrics(_improving_series())
    assert g["available"] is True
    assert g["revenue_cagr"] is not None
    assert g["revenue_cagr"] > 0  # revenue grew every period in the fixture


def test_trend_windows_answers_module_9_questions():
    windows = trend_windows(_improving_series())
    q = windows["questions"]
    assert "accelerating" in q["is_growth_accelerating"] or "decelerating" in q["is_growth_accelerating"] or "steady" in q["is_growth_accelerating"]
    assert q["are_margins_expanding"]
    assert q["is_leverage_improving"]
    assert q["is_capital_efficiency_increasing"]


# ---------------------------------------------------------------------------
# Financial Health Scoring Engine (Module 14)
# ---------------------------------------------------------------------------
def test_health_score_has_eight_subscores_and_overall():
    result = score_financial_health(_improving_series())
    assert result["available"] is True
    assert len(result["sub_scores"]) == 8
    for s in result["sub_scores"]:
        assert 0 <= s["score"] <= 10
        assert s["evidence"] is not None
        assert s["explanation"]
        assert 0 <= s["confidence"] <= 1
        assert s["historical_trend"]
    assert 0 <= result["overall_financial_strength"] <= 100


def test_health_score_higher_for_stronger_company():
    strong = score_financial_health(_improving_series())
    weak = score_financial_health(_pat_up_ocf_down_series())
    assert strong["overall_financial_strength"] >= weak["overall_financial_strength"]


# ---------------------------------------------------------------------------
# Industry Interpretation (Module 11)
# ---------------------------------------------------------------------------
def test_industry_lens_covers_all_five_spec_sectors():
    for sector in ("banks", "it_services", "retail", "hospitals", "oil_gas"):
        ctx = industry_context(sector)
        assert ctx["found"] is True
        assert ctx["sector_kpis"]


def test_bank_ratio_applicability_flags_debt_equity_not_meaningful():
    ctx = industry_context("banks")
    flagged = {r["ratio_key"]: r for r in ctx["ratio_applicability"]}
    assert flagged["debt_to_equity"]["role"] == "not_meaningful"
    assert flagged["current_ratio"]["role"] == "not_applicable"


# ---------------------------------------------------------------------------
# Case Study Library (Module 13)
# ---------------------------------------------------------------------------
def test_eight_case_studies_present():
    keys = {c["key"] for c in list_case_studies()}
    assert keys == {"apple", "microsoft", "reliance", "tcs", "infosys", "hdfcbank", "jsw_energy", "asian_paints"}


def test_case_studies_are_labelled_illustrative():
    for series in CASE_STUDIES.values():
        assert series.data_source == "illustrative_fixture_not_live"


@pytest.mark.parametrize("key", ["apple", "microsoft", "reliance", "tcs", "infosys", "hdfcbank", "jsw_energy", "asian_paints"])
def test_case_study_full_analysis_runs_clean(key):
    result = analyse_case_study(key)
    assert result["found"] is True
    assert result["overall_direction"]["verdict"] in ("improving", "deteriorating", "mixed")
    assert result["earnings_quality"]["available"] is True
    assert result["financial_health_score"]["available"] is True
    assert result["narrative"]["available"] is True
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)


# ---------------------------------------------------------------------------
# Bridge from Phase 1 (financial_foundations)
# ---------------------------------------------------------------------------
def test_adapter_bridges_phase1_output_to_phase2_schema():
    from financial_foundations.simulation import run_simulation

    phase1_result = run_simulation()
    period = statement_period_from_phase1(phase1_result, label="P1", sequence=1)
    assert period.revenue == phase1_result["income_statement"]["revenue"]
    assert period.pat == phase1_result["income_statement"]["pat"]
    assert period.cash == phase1_result["balance_sheet"]["assets"]["current_assets"]["cash"]


def test_production_health_and_dashboard():
    h = production.health()
    assert h["status"] == "ok"
    d = production.dashboard()
    assert d["rule_library_size"] >= 200
    assert d["case_studies"] == 8


def test_production_soft_slice_for_ask_agi():
    hit = production.soft_slice_for_ask_agi("What is ROIC?")
    assert hit["enabled"] is True
    miss = production.soft_slice_for_ask_agi("completely unrelated xyz")
    assert miss["enabled"] is False
