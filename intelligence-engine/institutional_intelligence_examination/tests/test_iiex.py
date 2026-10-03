"""IIEX v1.0 — CIO Institutional Intelligence Examination tests."""

from __future__ import annotations

from institutional_intelligence_examination.production import (
    dashboard,
    grades,
    health,
    history,
    questions,
    report,
    run,
)
from institutional_intelligence_examination.questions import total_marks
from institutional_intelligence_examination.schema import MODULE_CODE, NO_IIEX_ACTIONS, NORMALIZED_PASS
from institutional_intelligence_examination.store import reset


def setup_function() -> None:
    reset()


def test_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["module_code"] == MODULE_CODE == "IIEX"
    assert h["questions"] == 31
    assert h["total_marks_bank"] == total_marks() == 600
    assert h["pass_marks"] == NORMALIZED_PASS == 450
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    for a in NO_IIEX_ACTIONS:
        assert a in h["does_not"]


def test_questions_bank() -> None:
    pack = questions()
    assert pack["n"] == 31
    assert pack["total_marks_bank"] == 600
    assert pack["sections"]["A_Company"] == 100
    assert pack["sections"]["J_CIO_Committee"] == 65


def test_full_exam_agi_only() -> None:
    out = run()
    assert out["total_questions"] == 31
    assert out["internet_used"] is False
    assert out["providers_queried"] == []
    assert out["summary"]["marks_available"] == 600
    assert out["summary"]["normalized_500"] is not None
    assert out["summary"]["certification"] in {
        "INSTITUTIONAL READY",
        "PARTIALLY READY",
        "NOT READY",
    }
    for r in out["results"]:
        assert r["evidence_pack"]["internet_used"] is False
        assert r["evidence_pack"]["providers_queried"] == []
        assert r["score"]["marks_awarded"] >= 0
        assert r["answer"]["supporting_evidence"] or (r["answer"].get("sections") or {}).get(
            "supporting_evidence"
        )


def test_sample_questions() -> None:
    out = run(question_ids=["Q1", "Q25", "Q30", "Q31"])
    assert out["total_questions"] == 4
    ids = {r["question"]["id"] for r in out["results"]}
    assert ids == {"Q1", "Q25", "Q30", "Q31"}
    q25 = next(r for r in out["results"] if r["question"]["id"] == "Q25")
    blob = str(q25["answer"])
    assert "Bull" in blob and "Base" in blob and "Bear" in blob


def test_report_and_grades() -> None:
    run()
    rep = report()
    assert "markdown" in rep
    assert "Institutional Intelligence Examination" in rep["markdown"] or "IIE" in rep["markdown"]
    g = grades()
    assert g["normalized_500"] == rep["summary"]["normalized_500"]
    assert len(g["per_question"]) == 31
    board = dashboard()
    assert board["questions"] == 31
    assert board["pass_bar"] == 450
    hist = history()
    assert hist["n"] >= 1
