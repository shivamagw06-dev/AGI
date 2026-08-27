"""RH-01 — AGI Release Health tests."""

from __future__ import annotations

from release_health.production import dashboard, health, run
from release_health.schema import IBS_EXPECTED, IST_EXPECTED, RH_WORKSTREAM_ID
from release_health import store as rh_store


def setup_function(_fn=None):
    rh_store.reset_for_tests()


def test_health_access_paths():
    h = health()
    assert h["workstream_id"] == RH_WORKSTREAM_ID
    assert h["brand"] == "AGI"
    assert h["not_an_engine"] is True
    assert h["access"]["admin_ui"] == "/admin/release-health"
    assert "release_health --run" in h["access"]["cli"]


def test_release_gate_ready():
    result = run({"run_unit_tests": True})
    assert result["workstream_id"] == RH_WORKSTREAM_ID
    assert result["ist"]["display"] == f"{IST_EXPECTED}/{IST_EXPECTED}"
    assert result["ibs"]["passed"] >= IBS_EXPECTED
    assert result["e2e"]["ok"] is True
    assert result["hallucinations"] == 0
    assert result["broken_provenance"] == 0
    assert result["performance"] == "PASS"
    assert result["ready_for_release"] is True, result.get("gates")
    assert result["ready_for_release_label"] == "YES"


def test_dashboard_serves_snapshot():
    run({"run_unit_tests": False})
    d = dashboard(refresh=False)
    assert d["snapshot"]["ready_for_release"] is True


def test_dashboard_cold_start_skips_heavy_gate():
    """Plain GET must not require a prior run / pytest — lightweight assemble only."""
    d = dashboard(refresh=False)
    assert d["ok"] is True
    assert d["snapshot"]["workstream_id"] == RH_WORKSTREAM_ID
    assert d["snapshot"]["unit_tests"].get("skipped") is True


def test_run_defaults_skip_unit_tests():
    result = run({})
    assert result["unit_tests"].get("skipped") is True
