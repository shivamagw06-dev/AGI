"""PAT-01 — Production Acceptance Test (break AGIB before onboarding users)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from institutional_acceptance.production import (
    cases_api,
    health,
    report_api,
    reset_for_tests,
    run,
    soft_slice_mission_control,
)
from institutional_acceptance.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    PAT_COMPANIES,
    PAT_WORKSTREAM_ID,
    PHASES,
    SUCCESS_CRITERIA,
)
from institutional_acceptance.test_runner import run_all, run_phase


@pytest.fixture(autouse=True)
def _clean():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_is_acceptance_not_expansion():
    h = health()
    assert h["workstream_id"] == PAT_WORKSTREAM_ID
    assert h["is_production_acceptance"] is True
    assert h["is_feature_expansion"] is False
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert h["acceptance_center"] is True


def test_full_suite_meets_success_criteria():
    report = run_all(mode="harness")
    assert report["total"] >= SUCCESS_CRITERIA["min_test_cases"]
    assert report["total"] >= 200
    assert report["failed"] == 0
    assert report["critical_failures"] == 0
    assert report["architecture_score"] == 100
    assert report["security_violations"] == 0
    assert report["memory_leaks"] == 0
    assert report["pass_rate_pct"] == 100.0
    assert report["certified"] is True
    assert report["overall_result"] == "PRODUCTION CERTIFIED"
    assert "PRODUCTION CERTIFIED" in report["report_text"]


def test_all_fifteen_phases_present():
    report = run_all(mode="harness")
    phases = report["phases"]
    assert len(PHASES) == 15
    for _code, key, title in PHASES:
        assert key in phases, key
        assert phases[key]["status"] == "PASS", f"{title} not PASS"
        assert phases[key]["total"] > 0


def test_ask_agi_one_hundred_questions():
    cases = run_phase("ask_agi", mode="harness")
    assert len(cases) == 100
    assert all(c["status"] == "PASS" for c in cases)
    assert all(c["meta"]["checks"]["no_buy_generated"] for c in cases)


def test_intelligence_covers_fifty_companies():
    cases = run_phase("intelligence", mode="harness")
    tickers = {c["meta"]["ticker"] for c in cases}
    assert len(PAT_COMPANIES) == 50
    assert tickers == set(PAT_COMPANIES)
    assert len(cases) == 50 * 6  # observation/forecast/decision/risk/policy/committee


def test_security_attacks_rejected():
    cases = run_phase("security", mode="harness")
    attacks = [c for c in cases if c["id"].startswith("P09-") and "Reject" in c["name"]]
    assert len(attacks) >= 9
    assert all(c["status"] == "PASS" and c["meta"].get("actual") == "rejected" for c in attacks)


def test_soft_slice_acceptance_center():
    run_all(mode="harness")
    board = soft_slice_mission_control()
    assert board["acceptance_center"] is True
    assert board["certified"] is True
    assert board["workstream_id"] == PAT_WORKSTREAM_ID


def test_api_facades():
    out = run({"mode": "harness"})
    assert out["ok"] is True
    assert out["certified"] is True
    rep = report_api()
    assert rep["certified"] is True
    cases = cases_api(limit=50)
    assert cases["total"] >= 200
    assert len(cases["cases"]) == 50


def test_cli_pass():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "institutional_acceptance", "--quiet", "--mode", "harness"],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(root)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "PASS" in (proc.stdout or "")


def test_agib_version_file():
    candidates = [
        Path("/workspace/AGIB_VERSION"),
        Path(__file__).resolve().parents[2] / "AGIB_VERSION",
    ]
    text = ""
    for c in candidates:
        if c.is_file():
            text = c.read_text(encoding="utf-8").strip()
            break
    assert text == "1.0.0"
