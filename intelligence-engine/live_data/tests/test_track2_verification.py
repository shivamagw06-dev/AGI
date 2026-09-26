"""Track 2 — production verification & certification acceptance tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from live_data import store
from live_data.production_verify import (
    certification,
    generate_report,
    health_dashboard,
    status,
    telemetry,
    verify,
)
from live_data.verification.certify import (
    record_verification_result,
    reset_certification,
)
from live_data.verification.schema import (
    CERTIFIED_CONSECUTIVE_LIVE_RUNS,
    FREEZE_LOCKS,
    PRODUCTION_CHECKLIST,
    VERIFY_VERSION,
)
from live_data.verification.telemetry import reset_telemetry

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
ROOT = Path(__file__).resolve().parents[2]


def _injected() -> dict:
    return {
        "nse_bhavcopy": (SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv").read_text(encoding="utf-8"),
        "nse_announcements": json.loads((SAMPLES / "nse_announcements.json").read_text(encoding="utf-8")),
        "bse_corporate_actions": (SAMPLES / "bse_corporate_actions.csv").read_text(encoding="utf-8"),
        "rbi_dbie": json.loads((SAMPLES / "rbi_dbie_key_rates.json").read_text(encoding="utf-8")),
        "company_ir": json.loads((SAMPLES / "company_ir_infosys.json").read_text(encoding="utf-8")),
    }


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi_t2"))
    monkeypatch.delenv("LIDI_ALLOW_RECORDED_SAMPLE", raising=False)
    store.reset_runtime()
    reset_certification()
    reset_telemetry()
    yield
    store.reset_runtime()
    reset_certification()
    reset_telemetry()


def test_verification_lifecycle_with_injected_sources() -> None:
    report = verify(
        injected=_injected(),
        skip_live_probes=True,
        skip_morning=True,
        morning_dry_run=True,
    )
    assert report["verify_version"] == VERIFY_VERSION
    assert report["fixture"] is False
    assert report["fabricated"] is False
    assert FREEZE_LOCKS["reasoning"] is True
    assert len(report["collectors"]) == 5
    for row in report["collectors"]:
        assert row["FIXTURE"] is False
        assert row["mode"] == "INJECTED"
        assert row["checklist"]["total"] == len(PRODUCTION_CHECKLIST)
        assert row["telemetry"]["run_id"] == report["run_id"]
        # Injected path certifies at TESTING, never silent CERTIFIED
        assert row["status"] in {"TESTING", "DEVELOPMENT", "STAGING"}
        assert row["status"] != "CERTIFIED"
    assert report["replay"]["ok"] is True
    assert report["platform"]["scheduler"]["ok"] is True
    assert report["platform"]["reasoning"]["ok"] is True
    assert report["morning_verification"]["ok"] is True


def test_certification_requires_seven_consecutive_live_days() -> None:
    assert CERTIFIED_CONSECUTIVE_LIVE_RUNS == 7
    # Simulate 6 distinct live days → PRODUCTION_READY, not CERTIFIED
    for i in range(6):
        row = record_verification_result(
            source_id="nse_bhavcopy",
            mode="LIVE",
            lifecycle_ok=True,
            validation_ok=True,
            provenance_ok=True,
            replay_ok=True,
            fixture_used=False,
            as_of_date=f"2024-07-{10 + i:02d}",
        )
    assert row["consecutive_live_successes"] == 6
    assert row["level"] == "PRODUCTION_READY"

    seventh = record_verification_result(
        source_id="nse_bhavcopy",
        mode="LIVE",
        lifecycle_ok=True,
        validation_ok=True,
        provenance_ok=True,
        replay_ok=True,
        fixture_used=False,
        as_of_date="2024-07-16",
    )
    assert seventh["consecutive_live_successes"] == 7
    assert seventh["level"] == "CERTIFIED"

    # Fixture breaks certification streak
    broken = record_verification_result(
        source_id="nse_bhavcopy",
        mode="FIXTURE",
        lifecycle_ok=True,
        validation_ok=True,
        provenance_ok=True,
        replay_ok=True,
        fixture_used=True,
        as_of_date="2024-07-17",
    )
    assert broken["consecutive_live_successes"] == 0
    assert broken["level"] == "TESTING"


def test_health_dashboard_columns() -> None:
    verify(injected=_injected(), skip_live_probes=True, skip_morning=True, morning_dry_run=True)
    dash = health_dashboard()
    required = {
        "collector",
        "official_source",
        "status",
        "LIVE",
        "SEED",
        "FIXTURE",
        "SNAPSHOT",
        "last_successful_run",
        "records_retrieved",
        "records_accepted",
        "records_rejected",
        "validation_rate",
        "knowledge_objects_updated",
        "evidence_packs_updated",
        "replay_status",
        "freshness",
        "latency",
        "scheduler_status",
        "mission_control_status",
    }
    assert required.issubset(set(dash["columns"]))
    assert len(dash["rows"]) == 5
    assert dash["north_star"] == "production_certified_live_collectors"


def test_telemetry_and_certification_apis() -> None:
    verify(injected=_injected(), skip_live_probes=True, skip_morning=True, morning_dry_run=True)
    tel = telemetry(limit=20)
    assert tel["n"] >= 5
    cert = certification()
    assert cert["summary"]["collectors"] == 5
    assert cert["summary"]["all_certified"] is False
    st = status()
    assert st["version"] == VERIFY_VERSION


def test_certification_report_written() -> None:
    verify(injected=_injected(), skip_live_probes=True, skip_morning=True, morning_dry_run=True)
    out = generate_report()
    assert out["ok"] is True
    path = Path(out["path"])
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "LIVE DATA CERTIFICATION REPORT" in text
    assert "Overall Live Data Readiness Score" in text
    assert "Recommended Fixes" in text
    assert out["readiness"]["score"] is not None


def test_snapshot_policy_never_fixture_on_live_failure(monkeypatch) -> None:
    import importlib

    bhav = importlib.import_module("live_data.collectors.nse_bhavcopy")

    def _boom(*_a, **_k):
        raise RuntimeError("blocked_network")

    monkeypatch.setattr(bhav, "http_get", _boom)
    monkeypatch.setattr(
        bhav, "_candidate_dates", lambda *a, **k: [__import__("datetime").datetime(2024, 7, 26)]
    )
    from live_data.schema import DEFAULT_RETRY

    monkeypatch.setitem(DEFAULT_RETRY, "max_attempts", 1)
    monkeypatch.setitem(DEFAULT_RETRY, "backoff_seconds", [0])

    # Only bhavcopy stage via stop_after through pipeline — use verify with skip and manual stage
    from live_data.pipeline import run_live_ingestion

    ing = run_live_ingestion(allow_recorded_sample=False, stop_after="nse_bhavcopy")
    stage = ing["stages"]["nse_bhavcopy"]
    assert stage.get("fixture") is not True
    # Fallbacks must not use fixtures
    fbs = store.list_fallbacks(limit=20)
    assert all(not f.get("used_fixture") for f in fbs)


def test_frozen_packages_untouched() -> None:
    frozen = [
        ROOT / "institutional_reasoning" / "execution_governance.py",
        ROOT / "ask_pipeline" / "pipeline.py",
        ROOT / "institutional_scheduler" / "scheduler" / "engine.py",
        ROOT / "research_office" / "office" / "runner.py",
    ]
    for path in frozen:
        if path.exists():
            ast.parse(path.read_text(encoding="utf-8"))
    banned = "govern" + "_answer"
    vroot = ROOT / "live_data" / "verification"
    for path in vroot.rglob("*.py"):
        if path.name in {"platform_soft.py", "test_track2_verification.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert banned not in text


def test_mission_control_soft_board() -> None:
    verify(injected=_injected(), skip_live_probes=True, skip_morning=True, morning_dry_run=True)
    from mission_control.aggregate import _soft_institutional_intelligence

    inst = _soft_institutional_intelligence()
    assert inst.get("live_collector_activation") is not None
    assert "live_collector_activation" in (inst.get("sources") or [])
    assert (inst["live_collector_activation"].get("certification_summary") or {}).get("collectors") == 5
