"""AGI ICC — Institutional Confidence Calibration acceptance tests."""

from __future__ import annotations

from institutional_confidence_calibration import ICC_VERSION, apply_confidence_calibration, status
from institutional_confidence_calibration.engine import calibrate


def _eh(hid: str, text: str, eval_score: float, **extra: object) -> dict:
    return {
        "hypothesis_id": hid,
        "hypothesis": text,
        "status": extra.pop("status", "Plausible"),
        "preferred": extra.pop("preferred", False),
        "evaluation_score": eval_score,
        "support_score": extra.pop("support", 16.0),
        "conflict_score": 10.0,
        "conflict_raw": extra.pop("conflict_raw", 5.0),
        "coverage_score": extra.pop("coverage", 8.0),
        "historical_score": extra.pop("historical", 7.0),
        "framework_score": extra.pop("framework", 8.0),
        "framework": "FW_MARGIN_BRIDGE",
        "confidence": 0.6,
        "supporting_evidence": ["E1"],
        "contradicting_evidence": extra.pop("conflicts", []),
        "missing_evidence": extra.pop("missing", []),
        **extra,
    }


def _strong_stack(*, missing=None, conflict_raw=5.0, disagreements=None, fixture=False):
    ihe = {
        "outcome": "preferred",
        "evaluated_hypotheses": [
            _eh(
                "H1",
                "Input-cost inflation compressed margins",
                78,
                status="Preferred",
                preferred=True,
                conflict_raw=conflict_raw,
                missing=missing or [],
                conflicts=["E2"] if conflict_raw > 20 else [],
            ),
            _eh("H2", "Pricing pressure reduced prices", 55, support=12),
        ],
    }
    icr = {
        "n_cases": 2,
        "preferred_case": "base",
        "probability_distribution": {"base": 70.0, "bear": 30.0},
        "report": {
            "outcome": "deliberated",
            "preferred_case": "base",
            "key_disagreements": disagreements or [],
            "missing_evidence": missing or [],
            "probability_distribution": {"base": 70.0, "bear": 30.0},
        },
    }
    iew = {
        "n_eligible": 6,
        "n_conflicts": 1 if conflict_raw > 20 else 0,
        "ordered_evidence": [
            {"evidence_id": "E1", "weight_score": 24.0},
            {"evidence_id": "E3", "weight_score": 18.0},
        ],
        "conflicts": [{"a": "E1", "b": "E2", "resolved": False}] if conflict_raw > 20 else [],
        "fixture_dependence": fixture,
    }
    return iew, ihe, icr


def test_icc_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("institutional-confidence-calibration")
    assert ICC_VERSION.startswith("institutional-confidence-calibration")
    assert s["freeze_locks"]["committee_reasoning"] is True
    assert s["freeze_locks"]["no_llm_confidence"] is True
    assert s["manually_assigned"] is False


def test_deterministic_identical_inputs() -> None:
    iew, ihe, icr = _strong_stack()
    a = calibrate(
        question="Why did margins decline?",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        institutional_memory={"have_we_seen_this_before": True, "top_memory_ids": ["M1"]},
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        temporal_integrity={"temporal_ok": True},
        replay_integrity=True,
    )
    b = calibrate(
        question="Why did margins decline?",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        institutional_memory={"have_we_seen_this_before": True, "top_memory_ids": ["M1"]},
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        temporal_integrity={"temporal_ok": True},
        replay_integrity=True,
    )
    assert a["overall_confidence"] == b["overall_confidence"]
    assert a["report"]["confidence_reason"] == b["report"]["confidence_reason"]
    assert a["deterministic"] is True
    assert a["llm_used"] is False


def test_missing_evidence_lowers_confidence() -> None:
    iew, ihe, icr = _strong_stack()
    base = calibrate(
        question="Why did margins decline?",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    iew2, ihe2, icr2 = _strong_stack(
        missing=[{"item": "Management guidance on cost outlook", "severity": "high"}]
    )
    low = calibrate(
        question="Why did margins decline?",
        evidence_weighting=iew2,
        hypothesis_evaluation=ihe2,
        committee_reasoning=icr2,
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    assert low["overall_confidence"] < base["overall_confidence"]
    assert low["report"]["missing_evidence_penalty"] > 0


def test_committee_disagreement_lowers_confidence() -> None:
    iew, ihe, icr = _strong_stack()
    base = calibrate(
        question="Q",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    iew2, ihe2, icr2 = _strong_stack(
        disagreements=[
            {"a": "bull", "b": "bear"},
            {"a": "base", "b": "bear"},
            {"a": "bull", "b": "base"},
        ]
    )
    # Also flatten distribution for weaker agreement
    icr2["probability_distribution"] = {"bull": 34.0, "base": 36.0, "bear": 30.0}
    icr2["report"]["probability_distribution"] = icr2["probability_distribution"]
    icr2["n_cases"] = 3
    low = calibrate(
        question="Q",
        evidence_weighting=iew2,
        hypothesis_evaluation=ihe2,
        committee_reasoning=icr2,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    assert low["overall_confidence"] < base["overall_confidence"]


def test_conflict_lowers_confidence() -> None:
    iew, ihe, icr = _strong_stack(conflict_raw=5.0)
    base = calibrate(
        question="Q",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    iew2, ihe2, icr2 = _strong_stack(conflict_raw=35.0)
    low = calibrate(
        question="Q",
        evidence_weighting=iew2,
        hypothesis_evaluation=ihe2,
        committee_reasoning=icr2,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    assert low["overall_confidence"] < base["overall_confidence"]
    assert low["report"]["conflict_score"] < base["report"]["conflict_score"]


def test_strong_evidence_raises_confidence() -> None:
    weak_iew = {"n_eligible": 0, "ordered_evidence": [], "n_conflicts": 0}
    strong_iew, ihe, icr = _strong_stack()
    weak = calibrate(
        question="Q",
        evidence_weighting=weak_iew,
        hypothesis_evaluation={"outcome": "insufficient_evidence", "evaluated_hypotheses": []},
        committee_reasoning={"n_cases": 0, "report": {"outcome": "insufficient_evidence"}},
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    strong = calibrate(
        question="Q",
        evidence_weighting=strong_iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        institutional_memory={"have_we_seen_this_before": True, "top_memory_ids": ["M1"]},
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    assert strong["overall_confidence"] > weak["overall_confidence"]
    assert strong["report"]["confidence_reason"]
    assert "Confidence:" in strong["report"]["confidence_reason"]


def test_fixtures_never_increase_confidence() -> None:
    iew, ihe, icr = _strong_stack()
    base = calibrate(
        question="Q",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
    )
    iew_f, ihe_f, icr_f = _strong_stack(fixture=True)
    fixt = calibrate(
        question="Q",
        evidence_weighting=iew_f,
        hypothesis_evaluation=ihe_f,
        committee_reasoning=icr_f,
        replay_integrity=True,
        temporal_integrity={"temporal_ok": True},
        metadata={"fixture_dependence": True},
    )
    assert fixt["overall_confidence"] <= base["overall_confidence"]
    assert fixt["report"]["fixture_raised_confidence"] is False
    assert fixt["report"]["penalties"]["fixture_dependence"] > 0


def test_apply_soft_wire_flags() -> None:
    iew, ihe, icr = _strong_stack()
    out = apply_confidence_calibration(
        question="Why did margins decline?",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        framework_selection={"framework_ids": ["FW_MARGIN_BRIDGE"]},
        temporal_integrity={"temporal_ok": True},
        replay_integrity=True,
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["icr_changed"] is False
    assert pack["manually_assigned"] is False
    assert 0 <= pack["overall_confidence"] <= 100
    assert pack["report"]["temporal_integrity"] is True
    assert pack["report"]["replay_integrity"] is True
