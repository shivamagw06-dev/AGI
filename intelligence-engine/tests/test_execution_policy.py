"""Framework execution policy — select / score / sufficiency / narrative gate."""

from __future__ import annotations

from institutional_reasoning.execution_policy import (
    enforce_valuation_narrative,
    evaluate_frameworks,
    select_frameworks,
    soft_slice_for_ask_agi,
)


def test_valuation_question_selects_damodaran_and_history():
    sel = select_frameworks("Is Nifty IT expensive versus history?")
    assert sel["question_type"] == "Valuation"
    ids = {f["framework_id"] for f in sel["required_frameworks"]}
    assert "rel_val_damodaran" in ids
    assert "hist_multiples" in ids
    assert "margin_of_safety" in ids
    assert sel["required_frameworks"][0]["score"] >= 90


def test_insufficient_blocks_narrative_without_numbers():
    sel = soft_slice_for_ask_agi("Is Nifty IT expensive vs history?")
    report = evaluate_frameworks(
        sel,
        valuation={"company": {"name": "Nifty IT"}},
        company_analysis={"enabled": True, "valuation": {"label": "Fair"}},
        finance_retrieval={"hits": []},
    )
    assert report["narrative_allowed"] is False
    assert report["sufficient"] is False
    assert any(r["status"] == "insufficient_evidence" for r in report["results"])
    enforced = enforce_valuation_narrative(
        executive="Valuation looks fair.",
        house_label="Hold",
        report=report,
    )
    assert enforced["rewritten"] is True
    assert "incomplete" in (enforced["executive"] or "").lower()


def test_executed_when_metrics_present():
    sel = soft_slice_for_ask_agi("Is INFY expensive versus history?")
    report = evaluate_frameworks(
        sel,
        valuation={
            "forward_pe": 24.1,
            "peer_pe": 22.0,
            "trailing_pe": 26.0,
            "hist_percentile": 78,
            "growth": 0.12,
            "roe": 0.28,
            "intrinsic_value": 1800,
            "margin_of_safety": 0.12,
            "bear_case": "EPS -10%",
            "fcf": 1.2e10,
            "wacc": 0.11,
            "terminal_growth": 0.04,
            "earnings_yield": 0.04,
            "exit_multiple": 20,
        },
        company_analysis={"valuation_intelligence": {"forward_pe": 24.1, "percentile": 78}},
        finance_retrieval={"hits": [{"forward_pe": 24.1}]},
    )
    # At least relative + historical should execute with these fields
    executed_ids = {r["framework_id"] for r in report["results"] if r["status"] == "executed"}
    assert "rel_val_damodaran" in executed_ids or "hist_multiples" in executed_ids
    assert report["narrative_allowed"] is True or report["executed"] >= 1


def test_rejects_wrong_entity_valuation_model_for_nifty_it():
    sel = soft_slice_for_ask_agi("Is Nifty IT expensive versus history?")
    report = evaluate_frameworks(
        sel,
        valuation={
            "company": {"company_symbol": "IS"},
            # These numbers must not count: they belong to a different entity.
            "forward_pe": 24.1,
            "peer_pe": 22.0,
            "hist_percentile": 78,
            "growth": 0.12,
        },
        company_analysis={"ticker": "NIFTYIT"},
    )
    assert report["narrative_allowed"] is False
    assert "target_matched_valuation_evidence" in report["missing_evidence"]
    assert all(
        r["status"] == "insufficient_evidence"
        for r in report["results"][:2]
    )


def test_zero_valuation_placeholders_do_not_execute_frameworks():
    sel = soft_slice_for_ask_agi("Is Nifty IT expensive versus history?")
    report = evaluate_frameworks(
        sel,
        valuation={
            "company": {"company_symbol": "NIFTYIT"},
            "forward_pe": 0,
            "peer_pe": 0,
            "hist_percentile": 0,
            "growth": 0,
        },
        company_analysis={"ticker": "NIFTYIT"},
    )
    assert report["narrative_allowed"] is False
    assert report["executed"] == 0
