"""Academy Certification Suite V1 tests."""

from __future__ import annotations

from academy.certification.gate import certification_gate
from academy.certification.grading.scale import band_for
from academy.certification.production import dashboard, list_inventory, quality_gates
from academy.certification.runner import all_exams, inventory, run_certification, run_exam
from academy.certification.schema import ACS_VERSION
from academy.validation_suite.memory import reset_memory


def setup_function() -> None:
    reset_memory()


def test_grading_scale_bands():
    assert band_for(96)["label"] == "Institutional Excellence"
    assert band_for(91)["label"] == "Institutional Ready"
    assert band_for(86)["label"] == "Professional"
    assert band_for(81)["label"] == "Competent"
    assert band_for(72)["label"] == "Developing"
    assert band_for(65)["label"] == "Weak"
    assert band_for(40)["label"] == "Fail"


def test_exam_bank_counts():
    counts = inventory()["counts"]
    assert counts["business"] >= 50
    assert counts["financial"] >= 50
    assert counts["valuation"] >= 50
    assert counts["sector"] >= 40
    assert counts["macro"] >= 40
    assert counts["risk"] >= 40
    assert counts["management"] >= 30
    assert counts["ownership"] >= 30
    assert counts["total"] >= 400
    levels = set(inventory()["levels"])
    assert {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17} <= levels


def test_level3_synthesis_single_institutional_answer():
    exam = next(e for e in all_exams() if e.exam_id == "acs_l3_001")
    result = run_exam(exam)
    assert result["score"] >= 80
    answer = result["answer"].lower()
    assert "damodaran" in answer and "graham" in answer and "fisher" in answer
    assert "institutional" in answer
    assert result["provenance"]["verbatim_book_quotes"] is False


def test_level8_decision_not_bare_yes_no():
    exam = next(e for e in all_exams() if e.level == 8)
    result = run_exam(exam)
    assert result["score"] >= 80
    assert "business" in result["answer"].lower()
    assert "committee" in result["answer"].lower()
    assert result["answer"].strip().lower() not in {"yes", "no"}


def test_sampled_certification_and_merge_gate():
    suite = run_certification(limit_per_analyst=6)
    assert suite["version"] == ACS_VERSION
    cert = suite["certificate"]
    assert cert["overall_intelligence"] >= 80
    assert cert["certified"] is True
    assert "Institutional" in cert["grade"] or cert["grade"] in {
        "Competent",
        "Professional",
        "Institutional Ready",
        "Institutional Excellence",
    }
    gate = certification_gate(full=False, limit_per_analyst=6)
    assert gate["allow_merge"] is True
    assert gate["gate"] == "ACADEMY_CERTIFICATION_SUITE"


def test_quality_gates_and_dashboard():
    gates = quality_gates(full=False)
    assert gates["passed"] is True, gates
    assert gates["checks"]["business_exams_50"] is True
    assert gates["checks"]["certification_pass"] is True
    dash = dashboard()
    assert dash["programme"] == "AGI_ACADEMY_CERTIFICATION_SUITE"
    inv = list_inventory()
    assert inv["exam_count"] >= 400


def test_analyst_certification_business_sample():
    exams = [e for e in all_exams() if e.analyst == "business" and e.level == 6][:5]
    assert len(exams) == 5
    for e in exams:
        r = run_exam(e)
        assert r["score"] >= 70, (e.exam_id, r["details"])
