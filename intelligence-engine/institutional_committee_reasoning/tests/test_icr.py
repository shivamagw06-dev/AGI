"""AGI ICR — Institutional Committee Reasoning acceptance tests."""

from __future__ import annotations

from institutional_committee_reasoning import ICR_VERSION, apply_committee_reasoning, status
from institutional_committee_reasoning.engine import deliberate


def _eh(hid: str, text: str, eval_score: float, support: float, conflict: float = 0.0, **extra: object) -> dict:
    return {
        "hypothesis_id": hid,
        "hypothesis": text,
        "category": "Company",
        "framework": "FW_MARGIN_BRIDGE",
        "status": extra.pop("status", "Plausible"),
        "evaluation_score": eval_score,
        "support_score": support,
        "conflict_score": 10.0,
        "conflict_raw": conflict,
        "coverage_score": 8.0,
        "historical_score": 7.0,
        "framework_score": 8.0,
        "confidence": 0.6,
        "supporting_evidence": extra.pop("support_ids", ["E1"]),
        "contradicting_evidence": extra.pop("conflict_ids", []),
        "missing_evidence": extra.pop("missing", []),
        "citations": [{"evidence_id": "E1", "role": "support"}],
        "evaluation_reason": "test",
        **extra,
    }


def test_icr_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("institutional-committee-reasoning")
    assert ICR_VERSION.startswith("institutional-committee-reasoning")
    assert s["voting_engine"] is False
    assert s["freeze_locks"]["hypothesis_evaluation"] is True
    assert s["freeze_locks"]["no_voting_engine"] is True


def test_deterministic_and_probabilities_sum_100() -> None:
    ihe = {
        "outcome": "preferred",
        "evaluated_hypotheses": [
            _eh("H1", "Input-cost inflation compressed margins", 72, 18, 20, status="Preferred", conflict_ids=["E2"]),
            _eh("H2", "Pricing pressure reduced prices", 55, 14, 5, support_ids=["E3"]),
            _eh("H3", "Long-term growth optionality underpins strength", 48, 12, 0, support_ids=["E4"]),
        ],
    }
    a = deliberate(question="Why did margins decline?", hypothesis_evaluation=ihe, framework_ids=["FW_MARGIN_BRIDGE"])
    b = deliberate(question="Why did margins decline?", hypothesis_evaluation=ihe, framework_ids=["FW_MARGIN_BRIDGE"])
    assert a["n_cases"] == b["n_cases"]
    assert a["probability_distribution"] == b["probability_distribution"]
    dist = a["probability_distribution"]
    assert abs(sum(dist.values()) - 100.0) < 0.05
    assert a["voting_engine"] is False
    # Cases have required fields
    for role, case in (a.get("cases") or {}).items():
        if not case:
            continue
        assert case.get("underlying_assumptions")
        assert case.get("key_catalysts")
        assert case.get("key_risks")
        assert case.get("invalidation_conditions")
        assert case.get("contradictory_evidence") is not None


def test_roles_not_forced_three() -> None:
    # Single viable → base only
    ihe = {
        "outcome": "preferred",
        "evaluated_hypotheses": [
            _eh("H1", "Demand weakness reduced leverage", 70, 16, 5, status="Preferred"),
            _eh("H2", "Rejected noise", 10, 2, 0, status="Rejected"),
        ],
    }
    pack = deliberate(question="Why did margins decline?", hypothesis_evaluation=ihe)
    assert pack["cases"].get("base") is not None
    # May or may not have bull/bear — must not fabricate empty shells with fake evidence
    for role in ("bull", "bear"):
        c = pack["cases"].get(role)
        if c is not None:
            assert c.get("supporting_evidence")


def test_insufficient_explicit() -> None:
    pack = deliberate(
        question="Why?",
        hypothesis_evaluation={"outcome": "insufficient_evidence", "evaluated_hypotheses": []},
    )
    assert pack["report"]["outcome"] == "insufficient_evidence"
    assert pack["n_cases"] == 0
    assert pack["fabricated"] is False
    assert "Insufficient" in pack["report"]["committee_summary"]


def test_preferred_case_explained() -> None:
    out = apply_committee_reasoning(
        question="Why did the stock fall after earnings?",
        hypothesis_evaluation={
            "outcome": "preferred",
            "evaluated_hypotheses": [
                _eh("H1", "Guidance disappointment drove the move", 75, 18, 10, status="Preferred"),
                _eh("H2", "Valuation already expensive into the print", 50, 12, 0),
                _eh("H3", "Margin concern dominated reaction", 45, 11, 15, conflict_ids=["E9"]),
            ],
        },
        framework_ids=["FW_EXPECTATIONS"],
        institutional_memory={"have_we_seen_this_before": True, "top_memory_ids": ["MEM1"], "surface_bullets": ["prior miss"]},
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["ihe_changed"] is False
    report = pack["report"]
    assert report.get("why_preferred")
    assert report.get("preferred_case") in {"bull", "base", "bear"}
    assert report.get("forced_consensus") is False


def test_contradictory_evidence_retained() -> None:
    pack = deliberate(
        question="Why did margins decline?",
        hypothesis_evaluation={
            "outcome": "preferred",
            "evaluated_hypotheses": [
                _eh(
                    "H1",
                    "Input-cost inflation compressed margins",
                    70,
                    16,
                    40,
                    status="Preferred",
                    conflict_ids=["E_CONFLICT"],
                ),
                _eh("H2", "Growth strength and premium franchise", 40, 10, 0),
            ],
        },
    )
    base = pack["cases"].get("base")
    assert base is not None
    assert "E_CONFLICT" in (base.get("contradictory_evidence") or [])
