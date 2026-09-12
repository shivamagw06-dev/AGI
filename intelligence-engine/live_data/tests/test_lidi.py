"""LIDI acceptance tests — injected / recorded samples; never silent fixture fallback."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from live_data import store
from live_data.collectors.nse_bhavcopy import collect_nse_bhavcopy, parse_bhavcopy_csv
from live_data.pipeline import run_live_ingestion
from live_data.production import (
    collectors,
    dashboard,
    fallback,
    freshness,
    health,
    sources,
    status,
    validation,
)
from live_data.schema import FREEZE_LOCKS, LIDI_VERSION
from live_data.validators import validate_live_dataset

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
ROOT = Path(__file__).resolve().parents[2]


def _injected_payloads() -> dict:
    return {
        "nse_bhavcopy": (SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv").read_text(encoding="utf-8"),
        "nse_announcements": json.loads((SAMPLES / "nse_announcements.json").read_text(encoding="utf-8")),
        "bse_corporate_actions": (SAMPLES / "bse_corporate_actions.csv").read_text(encoding="utf-8"),
        "rbi_dbie": json.loads((SAMPLES / "rbi_dbie_key_rates.json").read_text(encoding="utf-8")),
        "company_ir": json.loads((SAMPLES / "company_ir_infosys.json").read_text(encoding="utf-8")),
    }


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.delenv("LIDI_ALLOW_RECORDED_SAMPLE", raising=False)
    monkeypatch.delenv("AGIB_ENV", raising=False)
    store.reset_runtime()
    yield
    store.reset_runtime()


def test_bhavcopy_parse_and_injected_collect() -> None:
    csv_text = (SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv").read_text(encoding="utf-8")
    effective, rows = parse_bhavcopy_csv(csv_text)
    assert effective == "2024-07-26"
    assert len(rows) >= 4
    assert rows[0]["symbol"] == "INFY"
    assert rows[0]["return_1d"] is not None

    env = collect_nse_bhavcopy(injected_csv=csv_text)
    assert env["ok"] is True
    assert env["fixture"] is False
    assert env["mode"] == "injected"
    assert env["checksum"]
    assert env["provenance"]["official_source"]
    assert env["available_from"] and env["retrieved_at"] and env["effective_date"]


def test_full_pipeline_with_injected_sources() -> None:
    report = run_live_ingestion(injected=_injected_payloads())
    assert report["fixture"] is False
    assert report["fabricated"] is False
    assert report["lidi_version"] == LIDI_VERSION
    stages = report["stages"]
    for sid in (
        "nse_bhavcopy",
        "nse_announcements",
        "bse_corporate_actions",
        "rbi_dbie",
        "company_ir",
    ):
        assert stages[sid]["ok"] is True, stages[sid]
        assert stages[sid]["fixture"] is False
        assert stages[sid]["mode"] == "injected"
    assert report["quality_gates"]["collectors_operational"] == 5
    assert report["quality_gates"]["passed"] is True
    assert report["publish"]["pack_count"] >= 4
    assert report["publish"]["fixture"] is False
    bundle = list((Path(os.environ["LIDI_STORE_ROOT"]) / "objects").glob("bundle_*.json"))
    assert bundle


def test_point_in_time_and_provenance_fields() -> None:
    csv_text = (SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv").read_text(encoding="utf-8")
    env = collect_nse_bhavcopy(injected_csv=csv_text)
    for key in ("available_from", "retrieved_at", "effective_date", "source_version"):
        assert env.get(key)
    prov = env["provenance"]
    for key in ("official_source", "collector", "retrieved_at", "confidence", "version"):
        assert key in prov
    verdict = validate_live_dataset(env)
    assert verdict["ok"] is True


def test_validator_rejects_fixtures_and_missing_provenance() -> None:
    bad = {
        "collector_id": "x",
        "source_id": "nse_bhavcopy",
        "official_source": "NSE",
        "effective_date": "2024-07-26",
        "fixture": True,
        "payload": {"rows": [{"symbol": "INFY", "close": 1.0, "date": "2024-07-26"}]},
        "provenance": {"official_source": "NSE"},
        "mode": "injected",
    }
    v = validate_live_dataset(bad)
    assert v["ok"] is False
    assert "fixture_not_allowed_in_lidi_publish" in v["failures"]


def test_no_silent_recorded_sample_without_flag(monkeypatch) -> None:
    import importlib

    bhav = importlib.import_module("live_data.collectors.nse_bhavcopy")
    from live_data.schema import DEFAULT_RETRY

    def _boom(*_a, **_k):
        raise RuntimeError("blocked_network")

    monkeypatch.setattr(bhav, "http_get", _boom)
    monkeypatch.setitem(DEFAULT_RETRY, "max_attempts", 1)
    monkeypatch.setitem(DEFAULT_RETRY, "backoff_seconds", [0])
    monkeypatch.setattr(
        bhav, "_candidate_dates", lambda *a, **k: [__import__("datetime").datetime(2024, 7, 26)]
    )

    report = run_live_ingestion(allow_recorded_sample=False, stop_after="nse_bhavcopy")
    stage = report["stages"]["nse_bhavcopy"]
    assert stage.get("fixture") is not True
    assert stage.get("ok") is False or stage.get("fallback") or stage.get("mode") == "snapshot"
    fb = fallback()
    assert fb["silent_fixture_fallbacks"] == 0
    assert fb["never_silent_fixture_fallback"] is True
    assert all(not r.get("used_fixture") for r in fb["fallbacks"])


def test_production_apis_and_dashboard() -> None:
    run_live_ingestion(injected=_injected_payloads())
    st = status()
    assert st["version"] == LIDI_VERSION
    assert st["fixture_collectors_disabled"] is True
    assert sources()["n"] == 5
    assert freshness()["sources"]
    assert collectors()["n"] >= 1
    assert validation()["n"] >= 1
    dash = dashboard()
    assert dash["north_star"] == "validated_live_data_not_fixtures"
    assert "live_sources" in dash
    assert health()["reasoning_untouched"] is True
    assert FREEZE_LOCKS["never_raw_to_reasoning"] is True


def test_replay_deterministic_checksum() -> None:
    csv_text = (SAMPLES / "nse_bhavcopy_cm26JUL2024bhav.csv").read_text(encoding="utf-8")
    a = collect_nse_bhavcopy(injected_csv=csv_text)
    b = collect_nse_bhavcopy(injected_csv=csv_text)
    assert a["checksum"] == b["checksum"]
    assert a["payload"]["row_count"] == b["payload"]["row_count"]


def test_reasoning_untouched() -> None:
    frozen = [
        ROOT / "institutional_reasoning" / "execution_governance.py",
        ROOT / "decision_quality" / "pipeline.py",
    ]
    for path in frozen:
        if path.exists():
            ast.parse(path.read_text(encoding="utf-8"))
    package_files = [
        p
        for p in (ROOT / "live_data").rglob("*.py")
        if p.parent.name != "tests" and not p.name.startswith("test_")
    ]
    for path in package_files:
        text = path.read_text(encoding="utf-8")
        assert "govern_answer" not in text, path
        assert "evaluate_decision" not in text, path


def test_scheduler_soft_wire_present() -> None:
    from institutional_scheduler.execution import handlers as h

    text = Path(h.__file__).read_text(encoding="utf-8")
    assert "run_morning_live_ingestion" in text
    assert "live_data_preferred" is not None
    assert "live_data_preferred" in text
