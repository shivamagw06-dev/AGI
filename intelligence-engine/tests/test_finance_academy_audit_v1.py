"""Smoke tests for Finance Academy Validation Audit harness (post-FAPI)."""

from __future__ import annotations

from academy.audit.harness import run_audit, static_engine_import_audit, write_report
from academy.fapi.usage import reset_usage_store


def test_static_engine_import_audit_detects_fapi_wiring():
    audit = static_engine_import_audit()
    assert audit["verdict"] != "NO_LOCKED_ENGINE_IMPORTS_ACADEMY"
    assert "ve" in audit["engines_importing_academy"]
    assert "ui" in audit["engines_importing_academy"]
    assert "irp" in audit["engines_importing_academy"]


def test_run_audit_passes_after_fapi(tmp_path):
    reset_usage_store()
    evidence = run_audit()
    assert evidence["inventory"]["concept_count"] >= 100
    assert evidence["exam_suite"]["passed"] == evidence["exam_suite"]["total"]
    assert evidence["final_verdict"]["overall_pass"] is True
    assert evidence["final_verdict"]["success_criteria"]["engines_consume_rather_than_bypass"] is True
    assert evidence["scores"]["knowledge_extraction"] == 100
    assert evidence["scores"]["knowledge_usage"] >= 85
    assert evidence["graph_traversal"]["production_traversal_by_ask_agi"] is True
    assert evidence["ab_test"]["material_change_in_ask_agi"] is True

    paths = write_report(evidence, tmp_path)
    md = paths["markdown"].read_text()
    assert "Part 1 — Knowledge usage" in md
    assert "Part 6 — Retrieval audit" in md
    assert "PASS — Finance Academy is actively learned" in md
