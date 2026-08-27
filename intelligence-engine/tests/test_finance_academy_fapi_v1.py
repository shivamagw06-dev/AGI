"""FAPI v1.0 — Finance Academy Production Integration tests."""

from __future__ import annotations

from academy.fapi.production import (
    apply_ve_assumptions,
    attach_for_engine,
    is_production_enabled,
    package_for_query,
    quality_gates,
    run_ab_probe,
)
from academy.fapi.usage import reset_usage_store
from academy.audit.harness import run_audit, static_engine_import_audit


def setup_function() -> None:
    reset_usage_store()


def test_fapi_enabled_by_default():
    assert is_production_enabled() is True


def test_package_for_finance_query_retrieves_multi_discipline():
    pkg = package_for_query("Why does ROIC matter more than revenue growth?", engine="ask_agi")
    assert pkg["enabled"] is True
    assert pkg["is_finance"] is True
    assert len(pkg["concept_ids"]) >= 3
    assert pkg["provenance"]["influenced"] is True
    assert pkg.get("answer_hints")


def test_ve_assumptions_differ_from_hardcoded_defaults():
    base = {
        "wacc": 0.11,
        "cost_of_equity": 0.13,
        "cost_of_debt": 0.08,
        "beta": 1.0,
        "risk_free_rate": 0.07,
        "tax_rate": 0.25,
    }
    out = apply_ve_assumptions(base)
    assert out["uses_academy_wacc_objects"] is True
    assert out["changed"] is True
    assert abs(float(out["assumptions"]["wacc"]) - 0.11) > 1e-9


def test_engines_attach_academy_slice():
    for eng in ("cae", "irp", "ve", "eve", "iie", "fle", "kf", "kcv", "ask_agi"):
        attached = attach_for_engine(eng, "Why is EBITDA different from cash flow?")
        assert attached["attached"] is True
        assert attached["finance_academy"]["concept_ids"]


def test_ab_probe_shows_material_improvement():
    ab = run_ab_probe("Why do higher interest rates reduce growth stock valuations?")
    assert ab["material_improvement"] is True
    assert ab["deltas"]["concepts_retrieved"] >= 1


def test_quality_gates_pass_after_warm():
    gates = quality_gates(warm=True)
    assert gates["passed"] is True
    assert gates["reject_completion"] is False


def test_static_import_audit_detects_production_wiring():
    audit = static_engine_import_audit()
    assert audit["verdict"] != "NO_LOCKED_ENGINE_IMPORTS_ACADEMY"
    importing = audit["engines_importing_academy"]
    for eng in ("ui", "irp", "ve", "eve", "iie", "fle", "kf", "cae"):
        assert eng in importing, f"{eng} should import academy/fapi"


def test_run_audit_passes_success_criteria():
    evidence = run_audit()
    assert evidence["final_verdict"]["overall_pass"] is True
    assert evidence["scores"]["knowledge_usage"] >= 85
    assert evidence["scores"]["overall_finance_academy_effectiveness"] >= 90
    assert evidence["ask_agi_probe"]["production_influenced"] is True
    assert evidence["ve_probe"]["uses_academy_wacc_objects"] is True
    assert evidence["ab_test"]["material_change_in_ask_agi"] is True
    assert evidence["ab_test"]["material_change_in_ve_defaults"] is True
