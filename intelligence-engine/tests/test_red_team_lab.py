"""AGIB Red Team lab tests — evaluation infrastructure, ECR, capability gate."""

from __future__ import annotations

from pathlib import Path

from red_team.bank import NEVER_TRAIN, RED_TEAM_BANK, REUSES_PRIOR_BENCHMARKS
from red_team.blind_runner import run_blind_item
from red_team.capability_gate import (
    gate_check,
    mark_production_allowed,
    register_failing_test,
)
from red_team.ecr import compute_ecr
from red_team.failure_db import build_failure_record
from red_team.production import health, quality_gates
from red_team.rules import CAPABILITY_GATE_RULE
from red_team.scorer import run_red_team_scorecard, score_blind_result


def test_red_team_rules_and_isolation():
    assert NEVER_TRAIN is True
    assert REUSES_PRIOR_BENCHMARKS is False
    assert len(RED_TEAM_BANK) >= 15
    # Engine modules must not import the Red Team bank.
    for rel in (
        "institutional_reasoning/bias_defense.py",
        "institutional_reasoning/adversarial.py",
        "institutional_reasoning/gold_patterns.py",
        "institutional_reasoning/family_composers.py",
    ):
        src = Path("/workspace/intelligence-engine") / rel
        text = src.read_text(encoding="utf-8")
        assert "red_team.bank" not in text
        assert "RED_TEAM_BANK" not in text
        assert "RT01" not in text


def test_health_and_gates():
    h = health()
    assert h["never_trains_the_engine"] is True
    assert h["separate_from_builders"] is True
    g = quality_gates()
    assert g["checks"]["evidence_to_conclusion_ratio"] is True
    assert g["checks"]["capability_gate"] is True


def test_engine_is_blind_to_category():
    item = RED_TEAM_BANK[0]
    blind = run_blind_item(item)
    assert blind["engine_saw_category"] is False
    assert "red_team_category" in blind
    # Packaged answer must not echo the internal category key as an instruction.
    packaged = blind["packaged"]
    assert packaged.get("owns_executive") is True


def test_ecr_counts_independent_sources():
    ecr = compute_ecr(
        conclusion="Margins improved on audited results.",
        answer_text=(
            "Supported by financial statements, an NSE filing, and macro data on rates."
        ),
        claimed_support=["Financial Statements", "Company Filing", "Macro Data"],
    )
    assert ecr["ecr"] >= 3
    assert ecr["confidence_band"] == "multi_source"
    weak = compute_ecr(
        conclusion="Demand is strong.",
        answer_text="A social media post and management commentary say so.",
    )
    assert weak["ecr"] <= 2
    assert weak["confidence_band"] in {"weak_single_source", "single_source", "moderate"}


def test_failure_record_template_fields():
    rec = build_failure_record(
        question="x",
        expected_category="anchoring",
        detected_family="valuation",
        detected_mode=None,
        evidence_used=["market_data"],
        evidence_missed=["financial_statements"],
        reasoning_mistake="Anchored on old price",
        editorial_mistake=None,
        root_cause="cognitive_trap",
        fix="Reject historical print as intrinsic value",
    )
    assert rec["question"] == "x"
    assert rec["expected_reasoning_family_or_category"] == "anchoring"
    assert rec["reasoning_mistake"]
    assert rec["root_cause"]
    assert rec["fix"]


def test_capability_gate_requires_failing_test_first(tmp_path: Path):
    reg = tmp_path / "gate.json"
    # Cannot allow without failing test.
    row = gate_check("new_feature_x", path=reg)
    assert row["allowed"] is False
    register_failing_test(
        capability_id="new_feature_x",
        test_id="RT_NEW_1",
        question="Brand new adversarial prompt that initially fails.",
        notes="Logged before implementation",
        path=reg,
    )
    allowed = mark_production_allowed(
        capability_id="new_feature_x",
        reason="Failing test on file; fix validated",
        path=reg,
    )
    assert allowed["production_allowed"] is True
    assert gate_check("new_feature_x", path=reg)["allowed"] is True
    assert CAPABILITY_GATE_RULE in gate_check("new_feature_x", path=reg)["rule"]


def test_red_team_scorecard_core_categories():
    report = run_red_team_scorecard(persist_failures=False)
    assert report["never_train"] is True
    assert report["engine_blind_to_categories"] is True
    assert report["consistency_group_ok"] is True
    # Lab should be strong on this v1 set after bias-defense process guards —
    # still interpreted as score-on-this-set only.
    assert report["score_per_100"] >= 80.0
    assert "genuine_reasoning" not in report["interpretation"]
    assert "this_red_team_set" in report["interpretation"]
    # Spot-check key categories
    by = report["by_category"]
    for cat in (
        "hidden_assumption",
        "survivorship_bias",
        "correlation_vs_causation",
        "adversarial_prompting",
        "anchoring",
    ):
        assert by[cat]["pass"] == by[cat]["total"], (cat, report["failures"])


def test_ask_agi_attaches_ecr():
    from institutional_reasoning.production import package_for_ask_agi

    out = package_for_ask_agi(
        query=(
            "A company's profit increased because it sold a major factory. Revenue was flat "
            "and operating cash flow declined. Is the business improving?"
        )
    )
    assert out.get("owns_executive") is True
    assert "ecr" in out
    assert "non-recurring" in (out.get("executive") or "").lower() or "one-off" in (
        out.get("executive") or ""
    ).lower()
