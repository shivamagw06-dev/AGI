"""Phase 3 acceptance — Institutional Knowledge Intelligence."""

from __future__ import annotations

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.iki.applicability import explain_dcf_for_entity
from institutional_reasoning.iki.production import quality_gates, run_judgement_suite
from institutional_reasoning.iki.registry import registry_snapshot


def test_framework_registry_is_data_not_hardcoded_map():
    reg = registry_snapshot()
    assert reg["n"] >= 8
    ids = {f["framework_id"] for f in reg["frameworks"]}
    assert "rel_val_damodaran" in ids
    assert "residual_income" in ids
    assert "buffett_quality" in ids


def test_dcf_hdfc_bank_not_applicable_residual_income_alternative():
    expl = explain_dcf_for_entity("HDFCBANK")
    assert expl["applicability"] == "No"
    assert "financial" in expl["reason"].lower() or "institution" in expl["reason"].lower()
    assert expl["alternative"] == "residual_income"

    record = govern_answer("Should DCF be used for HDFC Bank?")
    dcf = [f for f in record["frameworks"] if f["framework_id"] in {"dcf_applicability", "dcf_fcff"}]
    assert dcf
    assert all(f["status"] == "not_applicable" for f in dcf)
    debate = (record.get("iki") or {}).get("debate") or {}
    assert "residual" in str(debate.get("resolution") or "").lower()


def test_value_zomato_relative_dominates_graham_rejects():
    record = govern_answer("Value Zomato.")
    iki = record.get("iki") or {}
    scores = {s["framework_id"]: s for s in (iki.get("applicability") or {}).get("scores") or []}
    assert scores.get("rel_val_damodaran", {}).get("applicable") is True
    graham = scores.get("margin_of_safety") or scores.get("graham_net_net") or {}
    assert graham.get("applicable") is False
    authors = (iki.get("debate") or {}).get("authors") or {}
    assert authors.get("Graham", {}).get("stance") == "rejects"
    assert authors.get("Buffett", {}).get("stance") == "rejects"
    assert "domin" in str((iki.get("debate") or {}).get("resolution") or "").lower()


def test_buffett_vs_damodaran_conflict_explained():
    record = govern_answer("Compare Buffett and Damodaran on Zomato.")
    conflicts = (record.get("iki") or {}).get("debate", {}).get("conflicts") or []
    assert conflicts
    assert all(c.get("explanation") for c in conflicts)
    assert all(c.get("evidence_shown") for c in conflicts)


def test_institutional_judgement_suite_phase3_gate():
    ijs = run_judgement_suite()
    assert ijs["score"] >= 90.0
    assert ijs["phase3_gate"]["passed"] is True
    gates = quality_gates()
    assert gates["passed"] is True


def test_confidence_calibration_attached_to_plan():
    record = govern_answer("Is Infosys expensive?")
    order = (record.get("iki") or {}).get("execution_order") or []
    assert order
    assert order[0].get("confidence", {}).get("band") in {"High", "Medium", "Low"}
