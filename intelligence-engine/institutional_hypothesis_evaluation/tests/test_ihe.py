"""AGI IHE — Institutional Hypothesis Evaluation acceptance tests."""

from __future__ import annotations

from institutional_hypothesis_evaluation import IHE_VERSION, apply_hypothesis_evaluation, status
from institutional_hypothesis_evaluation.engine import evaluate_hypotheses


def _hyp(hid: str, text: str, support: float, conflict: float = 0.0, **extra: object) -> dict:
    return {
        "hypothesis_id": hid,
        "hypothesis": text,
        "category": "Company",
        "framework": "FW_MARGIN_BRIDGE",
        "template_key": extra.pop("template_key", hid.lower()),
        "supporting_evidence": extra.pop("support_ids", ["E1"]),
        "contradicting_evidence": extra.pop("conflict_ids", []),
        "support_score": support,
        "conflict_score": conflict,
        "weighted_support": support,
        "weighted_conflict": conflict,
        "overall_score": support - 0.65 * conflict,
        "status": "Active",
        "share": 0.3,
        **extra,
    }


def _ev(eid: str, title: str, weight: float) -> dict:
    return {
        "evidence_id": eid,
        "title": title,
        "source": "quarterly_results",
        "weight_score": weight,
        "eligible": True,
    }


def test_ihe_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("institutional-hypothesis-evaluation")
    assert IHE_VERSION.startswith("institutional-hypothesis-evaluation")
    assert s["freeze_locks"]["hypothesis_generation"] is True
    assert s["freeze_locks"]["no_forced_single_winner"] is True


def test_deterministic_identical_evaluations() -> None:
    ihg = {
        "hypotheses": [
            _hyp("H1", "Input-cost inflation compressed margins", 70, 10, support_ids=["E1"], conflict_ids=["E2"]),
            _hyp("H2", "Pricing pressure reduced prices", 55, 5, support_ids=["E3"]),
            _hyp("H3", "Demand weakness", 40, 0, support_ids=["E4"]),
        ]
    }
    iew = {
        "weighted_evidence": [
            _ev("E1", "COGS inflation", 70),
            _ev("E2", "Cost decline efficiency", 40),
            _ev("E3", "ASP pricing pressure", 55),
            _ev("E4", "Volume demand weakness", 40),
        ]
    }
    a = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation=ihg,
        evidence_weighting=iew,
        framework_ids=["FW_MARGIN_BRIDGE"],
    )
    b = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation=ihg,
        evidence_weighting=iew,
        framework_ids=["FW_MARGIN_BRIDGE"],
    )
    assert [h["hypothesis_id"] for h in a["evaluated_hypotheses"]] == [
        h["hypothesis_id"] for h in b["evaluated_hypotheses"]
    ]
    assert [h["evaluation_score"] for h in a["evaluated_hypotheses"]] == [
        h["evaluation_score"] for h in b["evaluated_hypotheses"]
    ]
    assert a["forced_single_winner"] is False


def test_conflicting_evidence_retained() -> None:
    pack = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation={
            "hypotheses": [
                _hyp("H1", "Input-cost inflation", 80, 50, support_ids=["E1"], conflict_ids=["E2"]),
                _hyp("H2", "Pricing pressure", 60, 0, support_ids=["E3"]),
            ]
        },
        evidence_weighting={
            "weighted_evidence": [
                _ev("E1", "cost inflation", 80),
                _ev("E2", "cost decline", 50),
                _ev("E3", "pricing pressure", 60),
            ]
        },
        framework_ids=["FW_MARGIN_BRIDGE"],
    )
    h1 = next(h for h in pack["evaluated_hypotheses"] if h["hypothesis_id"] == "H1")
    assert h1["contradicting_evidence"]
    assert float(h1["conflict_raw"]) > 0
    assert "Conflict retained" in (h1.get("evaluation_reason") or "")


def test_missing_evidence_lowers_confidence() -> None:
    base_ihg = {
        "hypotheses": [
            _hyp("H1", "Input-cost inflation", 70, 0, support_ids=["E1"]),
            _hyp("H2", "Pricing pressure", 50, 0, support_ids=["E2"]),
        ]
    }
    iew = {"weighted_evidence": [_ev("E1", "cost inflation", 70), _ev("E2", "pricing", 50)]}
    rich = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation=base_ihg,
        evidence_weighting=iew,
        framework_ids=["FW_MARGIN_BRIDGE"],
        playbook_selection={"evidence_required": []},
    )
    poor = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation=base_ihg,
        evidence_weighting=iew,
        framework_ids=["FW_MARGIN_BRIDGE"],
        playbook_selection={"evidence_required": ["audited cash flow bridge", "NPA disclosure", "guidance filing"]},
    )
    # Compare top hypothesis confidence
    c_rich = float((rich["report"].get("confidence") or 0))
    c_poor = float((poor["report"].get("confidence") or 0))
    assert c_poor <= c_rich
    assert (poor["report"].get("missing_evidence") or poor["evaluated_hypotheses"][0].get("missing_evidence"))


def test_balanced_remain_balanced() -> None:
    pack = evaluate_hypotheses(
        question="Why did margins decline?",
        hypothesis_generation={
            "hypotheses": [
                _hyp("H1", "Input-cost inflation", 65, 5, support_ids=["E1"]),
                _hyp("H2", "Pricing pressure", 64, 5, support_ids=["E2"]),
                _hyp("H3", "Demand weakness", 63, 5, support_ids=["E3"]),
            ]
        },
        evidence_weighting={
            "weighted_evidence": [
                _ev("E1", "cost inflation", 65),
                _ev("E2", "pricing pressure", 64),
                _ev("E3", "demand weakness", 63),
            ]
        },
        framework_ids=["FW_MARGIN_BRIDGE"],
    )
    assert pack["forced_single_winner"] is False
    assert pack["outcome"] in {"indeterminate", "plausible_set", "preferred"}
    if pack["outcome"] in {"indeterminate", "plausible_set"}:
        assert pack["report"]["preferred_hypothesis"] is None or pack["plural"] is True


def test_no_hallucinated_evaluations() -> None:
    pack = evaluate_hypotheses(
        question="Why?",
        hypothesis_generation={"insufficient_evidence": True, "hypotheses": [
            {"hypothesis_id": "X", "hypothesis": "Insufficient Evidence", "status": "InsufficientEvidence"}
        ]},
        evidence_weighting={"weighted_evidence": []},
    )
    assert pack["outcome"] == "insufficient_evidence"
    assert pack["fabricated"] is False
    assert pack["llm_used"] is False
    assert pack["n_evaluated"] == 0


def test_apply_soft_wire() -> None:
    out = apply_hypothesis_evaluation(
        question="Why did the stock fall after earnings?",
        hypothesis_generation={
            "hypotheses": [
                _hyp("H1", "Guidance disappointment", 75, 10, support_ids=["E1"], conflict_ids=["E2"], framework="FW_EXPECTATIONS"),
                _hyp("H2", "Valuation already expensive", 60, 0, support_ids=["E3"], framework="FW_HISTORICAL_VALUATION"),
            ]
        },
        evidence_weighting={
            "weighted_evidence": [
                _ev("E1", "guidance cut outlook miss", 75),
                _ev("E2", "raised guidance note", 30),
                _ev("E3", "expensive valuation multiple", 60),
            ]
        },
        framework_ids=["FW_EXPECTATIONS"],
        institutional_memory={"have_we_seen_this_before": True, "surface_bullets": ["prior guidance miss analog"]},
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["framework_changed"] is False
    assert pack["ihg_changed"] is False
    assert out["report"]["forced_single_winner"] is False
    assert pack["report"]["evaluation_version"].startswith("ihe-evaluation")
