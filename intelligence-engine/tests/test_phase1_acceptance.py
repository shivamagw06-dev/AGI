"""Phase 1 acceptance tests — evidence-first execution governance.

Test 1  missing historical PE          → cannot determine, NOT "expensive"
Test 2  wrong entity (IS vs NIFTYIT)   → execution blocked
Test 3  placeholder 52-week range = 0  → rejected
Test 4  education question             → Academy path, no evidence validation
Test 5  framework disagreement         → committee explains, nothing suppressed
"""

from __future__ import annotations

from institutional_reasoning.evidence_contracts import classify_question, resolve_entities
from institutional_reasoning.execution_governance import (
    enforce_editorial,
    govern_answer,
    governed_executive,
    telemetry_rows,
)

NIFTY_IT_Q = "Is Nifty IT expensive versus history?"


def _packs(**overrides):
    base = {
        "valuation": {},
        "company_analysis": {},
        "data_validation": {},
        "finance_retrieval": {},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------- Test 1
def test_1_missing_historical_pe_cannot_determine():
    # Isolate Phase 1 contract behaviour without Phase 2 pack injection.
    record = govern_answer(
        NIFTY_IT_Q,
        build_institutional_evidence=False,
        packs=_packs(
            data_validation={
                "validated": {
                    "trailing_pe": {
                        "field": "trailing_pe",
                        "symbol": "NIFTYIT",
                        "value": 31.4,
                        "verified_at": "2026-07-27T18:00:00Z",
                        "winning_provider": "dvc",
                    },
                    "peer_pe": {
                        "field": "peer_pe",
                        "symbol": "NIFTYIT",
                        "value": 27.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                        "winning_provider": "dvc",
                    },
                }
            }
        ),
    )
    assert record["question_type"] == "valuation"
    assert record["entity"]["entity_id"] == "NIFTYIT"
    assert "historical_pe" in record["missing_evidence"]
    assert record["narrative_allowed"] is False

    hist = next(f for f in record["frameworks"] if f["framework_id"] == "hist_multiples")
    assert hist["status"] == "insufficient_evidence"
    assert "historical_pe" in hist["missing_evidence"]

    executive = governed_executive(record)
    assert "withheld" in executive.lower() or "insufficient" in executive.lower()

    # Editorial cannot say "expensive"
    guarded = enforce_editorial(text="Nifty IT is expensive versus history.", record=record)
    assert guarded["blocked"] is True
    assert "expensive" in guarded["violations"]
    assert "expensive" not in guarded["text"].lower()


# ---------------------------------------------------------------- Test 2
def test_2_wrong_entity_blocks_execution():
    record = govern_answer(
        NIFTY_IT_Q,
        build_institutional_evidence=False,
        packs=_packs(
            valuation={
                "company": {"company_symbol": "IS"},
                "trailing_pe": 24.1,
                "historical_pe": 21.0,
                "historical_percentile": 78,
                "peer_pe": 22.0,
            }
        ),
    )
    assert record["entity"]["entity_id"] == "NIFTYIT"
    rejected = record["validation"]["rejected"]
    assert any(str(v).startswith("entity_mismatch") for v in rejected.values())
    assert record["narrative_allowed"] is False
    assert all(
        f["status"] in {"insufficient_evidence", "not_applicable"}
        for f in record["frameworks"]
    )


# ---------------------------------------------------------------- Test 3
def test_3_placeholder_values_rejected():
    record = govern_answer(
        NIFTY_IT_Q,
        build_institutional_evidence=False,
        packs=_packs(
            data_validation={
                "validated": {
                    "fifty_two_week_high": {
                        "field": "fifty_two_week_high",
                        "symbol": "NIFTYIT",
                        "value": 0.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                    "fifty_two_week_low": {
                        "field": "fifty_two_week_low",
                        "symbol": "NIFTYIT",
                        "value": 0.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                    "trailing_pe": {
                        "field": "trailing_pe",
                        "symbol": "NIFTYIT",
                        "value": 0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                }
            }
        ),
    )
    assert record["validation"]["rejected"].get("current_pe") == "placeholder_value"
    assert "current_pe" in record["missing_evidence"]
    assert record["narrative_allowed"] is False


# ---------------------------------------------------------------- Test 4
def test_4_education_bypasses_evidence_validation():
    record = govern_answer("What is ROIC?", packs=_packs(), academy={"concepts": ["roic"]})
    assert record["question_type"] == "education"
    assert record["path"] == "education"
    assert record["validation"] is None
    assert record["frameworks"] == []
    assert record["committee"] is None
    assert record["narrative_allowed"] is True

    guarded = enforce_editorial(
        text="ROIC measures return on invested capital.", record=record
    )
    assert guarded["blocked"] is False


# ---------------------------------------------------------------- Test 5
def test_5_committee_explains_framework_disagreement():
    record = govern_answer(
        NIFTY_IT_Q,
        packs=_packs(
            data_validation={
                "validated": {
                    "trailing_pe": {
                        "field": "trailing_pe",
                        "symbol": "NIFTYIT",
                        "value": 31.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                    "historical_pe": {
                        "field": "historical_pe",
                        "symbol": "NIFTYIT",
                        "value": 24.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                    "historical_percentile": {
                        "field": "historical_percentile",
                        "symbol": "NIFTYIT",
                        "value": 88,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                    # Peers richer than the index → peer-relative reads cheap
                    "peer_pe": {
                        "field": "peer_pe",
                        "symbol": "NIFTYIT",
                        "value": 36.0,
                        "verified_at": "2026-07-27T18:00:00Z",
                    },
                }
            }
        ),
    )
    committee = record["committee"]
    assert record["validation"]["complete"] is True
    assert committee["executed_count"] >= 2
    assert committee["disagreements"], "expected explicit disagreement"
    text = committee["conclusion"].lower()
    assert "disagree" in text
    assert "percentile" in text or "history" in text
    assert "peer" in text


# ------------------------------------------------------- governance extras
def test_dcf_not_applicable_for_index():
    record = govern_answer(NIFTY_IT_Q, packs=_packs())
    dcf = next(f for f in record["frameworks"] if f["framework_id"] == "dcf_applicability")
    assert dcf["status"] == "not_applicable"
    assert dcf["outputs"]["applicable"] is False


def test_unresolved_entity_requests_clarification():
    record = govern_answer("Is it expensive versus history?", packs=_packs())
    assert record["path"] == "clarification"
    assert record["narrative_allowed"] is False
    assert record["frameworks"] == []


def test_classification_matrix():
    assert classify_question("What is ROIC?")["question_type"] == "education"
    assert classify_question("Is Nifty IT expensive?")["question_type"] == "valuation"
    assert classify_question("Compare Infosys vs TCS")["question_type"] == "comparison"
    assert classify_question("Should I buy Infosys?")["question_type"] == "investment_decision"
    assert resolve_entities("Is Nifty IT expensive?")["primary"]["entity_type"] == "Index"


def test_telemetry_rows_are_per_framework_and_immutable_shaped():
    record = govern_answer(NIFTY_IT_Q, packs=_packs())
    rows = telemetry_rows(record, answer_id="ans_test_1")
    assert len(rows) == len(record["frameworks"])
    for row in rows:
        assert row["run_id"] == record["run_id"]
        assert row["question_type"] == "valuation"
        assert row["entity_id"] == "NIFTYIT"
        assert row["answer_id"] == "ans_test_1"
        assert row["execution_status"] in {
            "executed",
            "insufficient_evidence",
            "not_applicable",
        }
        assert "validation_result" in row
        assert "evidence_provenance" in row
