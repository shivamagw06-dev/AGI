"""AGI IHG — Institutional Hypothesis Generation acceptance tests."""

from __future__ import annotations

from institutional_hypothesis_generation import IHG_VERSION, apply_hypothesis_generation, status
from institutional_hypothesis_generation.engine import generate_hypotheses
from institutional_hypothesis_generation.production import explain


def _ev(eid: str, source: str, title: str, weight: float, **extra: object) -> dict:
    return {
        "evidence_id": eid,
        "source": source,
        "title": title,
        "weight_score": weight,
        "eligible": True,
        "reason": title,
        **extra,
    }


def test_ihg_status_branded() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["version"].startswith("institutional-hypothesis-generation")
    assert IHG_VERSION.startswith("institutional-hypothesis-generation")
    assert s["freeze_locks"]["no_llm_hypothesis"] is True
    assert s["freeze_locks"]["no_forced_single_winner"] is True
    assert s["forced_single_winner"] is False


def test_deterministic_identical_evidence() -> None:
    weighted = [
        _ev("E1", "quarterly_results", "Input cost inflation in COGS", 70),
        _ev("E2", "company_ir", "Pricing pressure from peers", 55),
        _ev("E3", "industry_research", "Demand weakness in volumes", 50),
        _ev("E4", "conference_call", "Product mix shift to lower-margin", 48),
    ]
    q = "Why did margins decline?"
    a = generate_hypotheses(question=q, weighted_evidence=weighted, weight_version="iew-v1")
    b = generate_hypotheses(question=q, weighted_evidence=weighted, weight_version="iew-v1")
    assert [h["hypothesis_id"] for h in a["hypotheses"]] == [h["hypothesis_id"] for h in b["hypotheses"]]
    assert [h["overall_score"] for h in a["hypotheses"]] == [h["overall_score"] for h in b["hypotheses"]]
    assert a["forced_single_winner"] is False


def test_weighted_evidence_influences_ranking() -> None:
    low_cost = [
        _ev("E1", "general_media", "Input cost inflation note", 20),
        _ev("E2", "audited_filing", "Pricing pressure disclosed", 90),
        _ev("E3", "industry_research", "Demand weakness", 40),
    ]
    high_cost = [
        _ev("E1", "audited_filing", "Input cost inflation in COGS", 95),
        _ev("E2", "general_media", "Pricing pressure rumour", 20),
        _ev("E3", "industry_research", "Demand weakness", 40),
    ]
    q = "Why did margins decline at the company?"
    r_low = generate_hypotheses(question=q, weighted_evidence=low_cost)
    r_high = generate_hypotheses(question=q, weighted_evidence=high_cost)
    # Find input-cost hypothesis ranks
    def rank_of(pack: dict, key: str) -> int:
        for h in pack["hypotheses"]:
            if h.get("template_key") == key:
                return int(h.get("priority") or 99)
        return 99

    assert rank_of(r_high, "input_cost_inflation") <= rank_of(r_low, "input_cost_inflation")


def test_conflicting_evidence_retained() -> None:
    weighted = [
        _ev("E1", "quarterly_results", "Input cost inflation raised COGS", 80),
        _ev("E2", "company_ir", "Efficiency gain and cost decline", 60),
        _ev("E3", "industry_research", "Pricing pressure in market", 50),
    ]
    pack = generate_hypotheses(question="Why did margins decline?", weighted_evidence=weighted)
    cost_h = next(h for h in pack["hypotheses"] if h.get("template_key") == "input_cost_inflation")
    assert cost_h["contradicting_evidence"]
    assert float(cost_h["conflict_score"]) > 0
    assert "conflict" in (cost_h.get("reason") or "").lower() or cost_h["weighted_conflict"] > 0


def test_rejected_hypotheses_explained_not_deleted() -> None:
    weighted = [
        _ev("E1", "quarterly_results", "Input cost inflation", 80),
        _ev("E2", "company_ir", "Pricing pressure", 70),
        _ev("E3", "social_media", "execution vibes only", 5),  # weak match possible
    ]
    pack = generate_hypotheses(question="Why did margins decline?", weighted_evidence=weighted)
    rejected = [h for h in pack["hypotheses"] if h.get("status") == "Rejected"]
    # May or may not reject depending on scores; if rejected, must explain
    for h in rejected:
        assert h.get("reason")
        assert "rejected" in (h.get("reason") or "").lower() or h.get("reject_reason")
    # Never delete — all candidates with support remain in list
    assert pack["n_hypotheses"] >= 2


def test_no_hallucinated_without_evidence() -> None:
    pack = generate_hypotheses(
        question="Why did margins decline?",
        weighted_evidence=[],
    )
    assert pack["insufficient_evidence"] is True
    assert pack["hypotheses"][0]["hypothesis"] == "Insufficient Evidence"
    assert pack["hypotheses"][0]["status"] == "InsufficientEvidence"
    assert pack["fabricated"] is False


def test_insufficient_evidence_when_cues_missing() -> None:
    # Evidence that doesn't match margin templates
    weighted = [
        _ev("E1", "general_media", "Celebrity endorsement unrelated", 40),
        _ev("E2", "social_media", "Meme stock chatter", 30),
    ]
    pack = generate_hypotheses(question="Why did margins decline?", weighted_evidence=weighted)
    assert pack["insufficient_evidence"] is True


def test_plural_outcomes_no_forced_winner() -> None:
    # Balanced support for two margin hypotheses
    weighted = [
        _ev("E1", "audited_filing", "Input cost inflation in COGS", 70),
        _ev("E2", "company_ir", "Pricing pressure on ASP", 68),
        _ev("E3", "industry_research", "Demand weakness in volumes", 30),
    ]
    pack = generate_hypotheses(question="Why did margins decline?", weighted_evidence=weighted)
    assert pack["forced_single_winner"] is False
    shares = [float(h.get("share") or 0) for h in pack["hypotheses"] if h.get("status") != "Rejected"]
    assert abs(sum(shares) - 1.0) < 0.02 or pack["outcome"] == "insufficient_evidence"
    if pack["outcome"] == "contested":
        contested = [h for h in pack["hypotheses"] if h.get("status") == "Contested"]
        assert len(contested) >= 2


def test_hdfc_premium_family() -> None:
    weighted = [
        _ev("E1", "annual_report", "Higher ROE versus peers", 85),
        _ev("E2", "regulator", "Superior asset quality NNPA", 80),
        _ev("E3", "company_ir", "Deposit franchise and CASA strength", 75),
        _ev("E4", "broker_research", "Long-term growth in loans", 60),
    ]
    pack = generate_hypotheses(
        question="Why is HDFC Bank trading at a premium?",
        weighted_evidence=weighted,
    )
    assert pack["insufficient_evidence"] is False
    assert pack["n_hypotheses"] >= 2
    keys = {h.get("template_key") for h in pack["hypotheses"]}
    assert "higher_roe" in keys or "asset_quality" in keys or "deposit_franchise" in keys


def test_apply_soft_wire_pack() -> None:
    iew = {
        "weight_version": "iew-weight-profile-v1.0.0",
        "weighted_evidence": [
            _ev("E1", "quarterly_results", "Guidance cut and outlook miss", 80),
            _ev("E2", "bloomberg", "Valuation already expensive multiple", 70),
            _ev("E3", "conference_call", "Margin concern in commentary", 65),
            _ev("E4", "company_ir", "Weak cash flow conversion", 55),
        ],
    }
    out = apply_hypothesis_generation(
        question="Why did the stock fall after earnings?",
        evidence_weighting=iew,
        intent="Explain",
        framework_ids=["FW_EXPECTATIONS"],
        playbook_id="PB_EARNINGS",
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["llm_used"] is False
    assert pack["iew_changed"] is False
    assert out["report"]["forced_single_winner"] is False
    exp = explain({"question": "Why did the stock fall after earnings?", "evidence_weighting": iew})
    assert exp.get("reason")


def test_replay_safe_stable_ids() -> None:
    weighted = [
        _ev("E1", "quarterly_results", "Input cost inflation", 70),
        _ev("E2", "company_ir", "Pricing pressure", 60),
    ]
    q = "Why did margins decline in FY24?"
    a = generate_hypotheses(question=q, weighted_evidence=weighted, as_of="2024-03-31")
    b = generate_hypotheses(question=q, weighted_evidence=weighted, as_of="2024-03-31")
    assert a["hypotheses"][0]["hypothesis_id"] == b["hypotheses"][0]["hypothesis_id"]
