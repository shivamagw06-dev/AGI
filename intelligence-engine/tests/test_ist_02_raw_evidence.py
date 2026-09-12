"""IST-02 — raw evidence institutional research validation."""

from __future__ import annotations

from institutional_stress_tests.pipeline_ist02 import run_ist02
from institutional_stress_tests.production import health, run_raw_evidence
from institutional_stress_tests.raw_corpus import kotak_rbi_april_2024_raw_corpus
from institutional_stress_tests.schema_ist02 import IST02_CASE_ID, IST02_PASS_SCORE, IST02_REPORT_SECTIONS
from institutional_stress_tests import store as ist_store


def setup_function(_fn=None):
    ist_store.reset_for_tests()


def test_health_exposes_ist02():
    h = health()
    assert "IST-02" in h["cases"]
    assert h["ist02"]["raw_evidence_only"] is True
    assert h["ist02"]["no_fixture_answers"] is True
    assert h["ist02"]["pass_score"] == IST02_PASS_SCORE


def test_raw_corpus_has_no_fixture_answers():
    corpus = kotak_rbi_april_2024_raw_corpus()
    assert corpus["fixture_answers"] is False
    assert corpus["prewritten_conclusions"] is False
    assert corpus["document_count"] >= 10
    types = {d["evidence_type"] for d in corpus["documents"]}
    for required in (
        "financial_statement",
        "regulatory_filing",
        "earnings_call",
        "peer_financial",
        "historical_price",
    ):
        assert required in types


def test_ist02_pass_from_raw_evidence():
    result = run_ist02(IST02_CASE_ID)
    assert result["raw_evidence_only"] is True
    assert result["fixture_answers_used"] is False
    assert result["passed"] is True, (result.get("failure_codes"), result.get("score"))
    assert result["research_quality_score"] >= IST02_PASS_SCORE
    report = result["institutional_report"]
    for key in IST02_REPORT_SECTIONS:
        assert key in report["sections"], key
    assert report["buy_sell"] is None
    assert report["collapsed_to_buy_sell"] is False
    # Citations required
    conf = report["sections"]["confidence_discussion"]
    assert conf["drivers_increasing_confidence"]
    assert conf["drivers_reducing_confidence"]
    assert conf["reason_confidence_cannot_be_higher"]
    assert report["sections"]["evidence_contradicting"]["items"]
    assert report["sections"]["outstanding_unknowns"]["items"]
    mon = report["sections"]["monitoring_framework"]
    assert mon["next_quarter"] and mon["six_month"] and mon["twelve_month"]
    assert report["sections"]["counterfactual_analysis"]["items"]


def test_fixture_answers_auto_fail():
    result = run_ist02(IST02_CASE_ID, fixture_answers={"q12": "Buy Kotak"})
    assert result["passed"] is False
    assert "FIXTURE_ANSWER_USED" in result["failure_codes"]


def test_empty_corpus_fails():
    result = run_ist02(IST02_CASE_ID, corpus={"ticker": "KOTAKBANK", "documents": [], "peers": []})
    assert result["passed"] is False
    assert "RAW_CORPUS_EMPTY" in result["failure_codes"]


def test_evidence_matrix_and_coverage():
    result = run_raw_evidence()
    assert result["evidence_matrix"]
    assert result["coverage_summary"]["document_count"] >= 10
    assert result["coverage_summary"]["citation_coverage"] > 0
    # Every matrix row cites corpus evidence
    corpus_ids = {d["evidence_id"] for d in kotak_rbi_april_2024_raw_corpus()["documents"]}
    for row in result["evidence_matrix"]:
        assert row["evidence_id"] in corpus_ids


def test_every_conclusion_paragraph_has_citations():
    result = run_ist02()
    sections = result["institutional_report"]["sections"]
    for key, sec in sections.items():
        for p in (sec.get("paragraphs") or []):
            assert p.get("evidence_ids"), key
            assert p.get("orphan") is False
