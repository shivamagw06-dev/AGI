"""IB-01 — AGIB Institutional Benchmark (competitive intelligence grade)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from institutional_grade_benchmark.production import (
    blind_vote_api,
    health,
    productivity_api,
    report_api,
    reset_for_tests,
    run,
    soft_slice_mission_control,
)
from institutional_grade_benchmark.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    IB_COMPANIES,
    IB_WORKSTREAM_ID,
    PASS_THRESHOLD,
    SECTIONS,
    TOTAL_POINTS,
)
from institutional_grade_benchmark.runner import run_all
from institutional_grade_benchmark import store


@pytest.fixture(autouse=True)
def _clean():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_is_competitive_not_pat_or_ibs():
    h = health()
    assert h["workstream_id"] == IB_WORKSTREAM_ID
    assert h["is_competitive_intelligence_test"] is True
    assert h["is_software_acceptance"] is False
    assert h["distinct_from_pat"] is True
    assert h["distinct_from_ibs"] is True
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert h["total_points"] == TOTAL_POINTS
    assert h["pass_threshold"] == PASS_THRESHOLD
    assert h["benchmark_center"] is True


def test_scale_and_sections():
    assert TOTAL_POINTS == 1000
    assert PASS_THRESHOLD == 900
    assert len(SECTIONS) == 8
    assert sum(m for *_rest, m in SECTIONS) == 1000
    assert len(IB_COMPANIES) == 20


def test_harness_scorecard_meets_threshold_provisional():
    report = run_all(mode="harness")
    assert report["total_score"] >= PASS_THRESHOLD
    assert report["institutional_grade"] is True
    assert report["provisional"] is True
    assert report["claim_safe"] is False
    assert "Institutional Grade" in report["report_text"]
    assert "software works" in report["report_text"].lower() or "software works" in report["guiding_principle"].lower()
    by = {s["code"]: s for s in report["sections"]}
    assert by["A"]["score"] >= 180
    assert by["F"]["score"] == 100  # unbroken lineage
    assert by["C"]["score"] >= 90


def test_company_research_covers_twenty():
    report = run_all(mode="harness")
    a = next(s for s in report["sections"] if s["key"] == "company_research")
    assert len(a["items"]) == 20
    tickers = {i["ticker"] for i in a["items"]}
    assert "HDFCBANK" in tickers and "RELIANCE" in tickers and "TCS" in tickers


def test_blind_panel_updates_score_and_claim_safe_path():
    for i in range(3):
        blind_vote_api(
            {
                "analyst_id": f"analyst.{i}",
                "preferred_label": "AGIB",
                "ranking": ["AGIB", "Report A", "Report B", "Report C", "Report D"],
            }
        )
    productivity_api(
        {
            "group": "bloomberg",
            "completion_time_min": 90,
            "confidence": 0.7,
            "quality": 0.75,
        }
    )
    productivity_api(
        {
            "group": "agib",
            "completion_time_min": 55,
            "confidence": 0.8,
            "quality": 0.82,
        }
    )
    assert store.panel_complete() is True
    report = run_all(mode="harness")
    b = next(s for s in report["sections"] if s["key"] == "blind_comparison")
    assert b["harness_estimate"] is False
    assert b["score"] == 200
    g = next(s for s in report["sections"] if s["key"] == "analyst_productivity")
    assert g["harness_estimate"] is False
    assert report["panel_complete"] is True
    # Other sections still harness estimates → claim_safe stays false until full live audit
    assert report["institutional_grade"] is True


def test_broken_lineage_fails_explainability():
    from institutional_grade_benchmark.sections import explainability as ex

    # Force broken hop via monkeypatch of probe
    original = ex._probe_lineage_hop
    ex._probe_lineage_hop = lambda hop: hop != "evidence"  # noqa: E731
    try:
        out = ex.score_explainability(mode="live")
        assert out["score"] == 0
        assert out["meta"]["broken_lineage"] is True
    finally:
        ex._probe_lineage_hop = original


def test_soft_slice_and_apis():
    run({"mode": "harness"})
    board = soft_slice_mission_control()
    assert board["benchmark_center"] is True
    assert board["institutional_grade"] is True
    rep = report_api()
    assert rep["total_max"] == 1000


def test_cli_pass():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "institutional_grade_benchmark", "--quiet", "--mode", "harness"],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "PASS" in (proc.stdout or "")


def test_distinct_package_from_ibs():
    import institutional_benchmarks
    import institutional_grade_benchmark

    assert institutional_benchmarks.IBS_WORKSTREAM_ID == "IBS-01"
    assert institutional_grade_benchmark.IB_WORKSTREAM_ID == "IB-01"
    assert institutional_benchmarks.IBS_WORKSTREAM_ID != institutional_grade_benchmark.IB_WORKSTREAM_ID
