"""IST-01 — Kotak RBI stress test: orchestration hard-gate + failure conditions."""

from __future__ import annotations

from institutional_stress_tests.fixtures import buy_without_evidence_answers, complete_answers, fire_prebuilt
from institutional_stress_tests.orchestration import evaluate_orchestration
from institutional_stress_tests.production import health, soft_slice_mission_control
from institutional_stress_tests.runner import run_case
from institutional_stress_tests.schema import IST01_CASE_ID, REQUIRED_MODULES
from institutional_stress_tests import store as ist_store


def setup_function(_fn=None):
    ist_store.reset_for_tests()


def test_health_declares_no_single_module_pass():
    h = health()
    assert h["workstream_id"] == "IST-01"
    assert h["no_single_module_pass"] is True
    assert h["forbids_buy_sell_verdict"] is True
    assert set(REQUIRED_MODULES).issubset(set(h["required_modules"]))


def test_single_module_cannot_pass():
    """Core requirement: no individual module can pass on its own."""
    for mod in ("FIRE-06", "CIO-01", "FSE", "AskAGI", "WO-01"):
        result = run_case(
            IST01_CASE_ID,
            prebuilt=fire_prebuilt(),
            answers=complete_answers(),
            modules_filter=[mod],
        )
        assert result["passed"] is False, mod
        fails = result["score"]["automatic_failures"]
        assert "SINGLE_MODULE_RESPONSE" in fails or "MISSING_REQUIRED_MODULES" in fails, (mod, fails)
        assert result["score"]["gates"]["orchestration"] is False


def test_orchestration_requires_all_required_modules():
    probes = {
        "FIRE-01": {"contributing": True},
        "FIRE-06": {"contributing": True},
    }
    orch = evaluate_orchestration(probes)
    assert orch["ok"] is False
    assert "MISSING_REQUIRED_MODULES" in orch["failures"]
    assert orch["single_module"] is False  # two modules, but still incomplete


def test_full_stack_institutional_view_can_pass():
    result = run_case(
        IST01_CASE_ID,
        prebuilt=fire_prebuilt(),
        answers=complete_answers(),
    )
    orch = result["score"]["orchestration"]
    assert orch["missing_required"] == [], orch
    assert orch["ok"] is True
    assert result["score"]["gates"]["orchestration"] is True
    assert result["score"]["gates"]["answer_contract"] is True
    assert result["passed"] is True
    assert result["score"]["weighted_total"] >= 70.0
    view = result["answer"]["final_institutional_view"]
    assert view.get("recommendation") in (None, "")
    assert view.get("evidence_against")
    assert view.get("remaining_unknowns")
    assert "BUY" not in str(view.get("investment_thesis") or "").upper() or "rather than" in str(
        view.get("investment_thesis") or ""
    ).lower()


def test_buy_without_evidence_auto_fails():
    result = run_case(
        IST01_CASE_ID,
        prebuilt=fire_prebuilt(),
        answers=buy_without_evidence_answers(),
    )
    assert result["passed"] is False
    fails = set(result["score"]["automatic_failures"])
    assert "BUY_WITHOUT_EVIDENCE" in fails or "COLLAPSED_TO_BUY_SELL" in fails
    assert "NO_UNKNOWNS_IDENTIFIED" in fails


def test_required_questions_present_on_pass_path():
    result = run_case(
        IST01_CASE_ID,
        prebuilt=fire_prebuilt(),
        answers=complete_answers(),
    )
    sections = result["answer"]["sections"]
    for key in (
        "what_happened",
        "what_caused_it",
        "temporary_or_structural",
        "management_diagnosis",
        "execution_vs_promises",
        "financial_quality_evolution",
        "competitor_performance",
        "relative_business_quality",
        "evidence_against",
        "evidence_supporting",
        "missing_evidence",
        "final_institutional_view",
    ):
        assert key in sections


def test_mission_control_panels():
    run_case(IST01_CASE_ID, prebuilt=fire_prebuilt(), answers=complete_answers())
    slice_ = soft_slice_mission_control()
    assert "runs" in slice_["panels"]
    assert slice_["no_single_module_pass"] is True
