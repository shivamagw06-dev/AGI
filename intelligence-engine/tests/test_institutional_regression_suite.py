"""Institutional Regression Suite V1 — Did this PR make AGIB smarter?"""

from __future__ import annotations

from academy.regression.golden_set.v1.companies import universe_counts
from academy.regression.golden_set.v1.questions import GOLDEN_QUESTIONS
from academy.regression.production import (
    admin_page,
    dashboard,
    quality_gates,
    release_gate,
    reset_for_tests,
    run_regression,
)
from academy.regression.schema import IRS_VERSION


def setup_function() -> None:
    reset_for_tests()


def test_frozen_universe_targets():
    counts = universe_counts()
    assert counts["targets_met"] is True
    assert counts["india_ge_100"] is True
    assert counts["buckets"]["banks"] >= 20
    assert counts["buckets"]["global"] >= 50
    assert counts["buckets"]["historical_failures"] >= 30
    assert counts["total"] >= 300


def test_golden_questions_immutable_set():
    domains = {q.domain for q in GOLDEN_QUESTIONS}
    assert {"business", "financial", "valuation", "risk", "macro", "sector", "portfolio"} <= domains
    assert len(GOLDEN_QUESTIONS) >= 15


def test_regression_run_improves_or_holds_vs_baseline():
    out = run_regression(release="test-v1", persist=True)
    assert out["irs_version"] == IRS_VERSION
    assert out["primary_question"].startswith("Did this pull request")
    iq = out["delta"]["overall_institutional_iq"]
    assert iq["current"] >= 70
    assert iq["delta"] >= -0.05  # no material regression vs baseline
    assert out["benchmark"]["hallucinations"].get("critical", 0) == 0
    assert out["gate"]["merge_status"] in {"APPROVED", "BLOCKED"}
    assert "Institutional Regression Report" in out["report"]["text"]


def test_release_gate_approved_on_healthy_run():
    gate = release_gate(release="test-gate", persist=True)
    assert gate["gate"] == "INSTITUTIONAL_REGRESSION_SUITE"
    assert gate["allow_merge"] is True
    assert gate["merge_status"] == "APPROVED"


def test_knowledge_retention_and_case_transfer():
    out = run_regression(release="test-retain", persist=False)
    assert out["benchmark"]["knowledge_retention"]["roic_synthesis_retained"] is True
    assert out["benchmark"]["case_transfer"]["count"] >= 3
    assert out["benchmark"]["case_transfer"]["all_pass"] is True


def test_quality_gates_and_admin():
    gates = quality_gates()
    assert gates["passed"] is True, gates
    dash = dashboard()
    assert dash["programme"] == "AGIB_INSTITUTIONAL_REGRESSION_SUITE"
    html = admin_page()
    assert "Institutional Regression Suite" in html
    assert "Did this pull request make AGIB smarter?" in html


def test_history_appends_immutably():
    run_regression(release="hist-a", persist=True)
    run_regression(release="hist-b", persist=True)
    from academy.regression.history.store import all_releases

    releases = all_releases()
    # baseline + hist-a + hist-b
    assert len(releases) >= 3
    names = [r["release"] for r in releases]
    assert "baseline" in names
    assert "hist-a" in names
    assert "hist-b" in names
