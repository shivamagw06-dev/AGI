"""Mission Control V1 — read-only administrator operations cockpit."""

from __future__ import annotations

from mission_control.flags import flags_dict
from mission_control.production import (
    acknowledge_alert,
    dashboard,
    health,
    quality_gates,
    reset_for_tests,
    system_report,
)
from mission_control.schema import MISSION_CONTROL_VERSION, PROGRAMME
from mission_control import snapshot as mc_snapshot


def setup_function() -> None:
    reset_for_tests()
    # Dashboard is snapshot-backed; seed a stub desk for section assertions.
    mc_snapshot.build_and_persist_snapshot(trigger="test_seed")


def test_flags_default_enabled():
    flags = flags_dict()
    assert flags["MISSION_CONTROL"] is True
    assert flags["MISSION_CONTROL_APIS"] is True
    assert flags["MISSION_CONTROL_PLATFORMS"] is True
    assert flags["MISSION_CONTROL_REPORTS"] is True


def test_health_payload():
    body = health()
    assert body["status"] == "ok"
    assert body["programme"] == PROGRAMME
    assert body["version"] == MISSION_CONTROL_VERSION
    assert body["architecture_status"] == "v1.0.1 LOCKED"
    assert body["read_only"] is True
    assert body["not_an_engine"] is True
    assert body["not_client_facing"] is True
    assert body["never_modifies_research"] is True
    assert "flags" in body


def test_dashboard_sections_present():
    body = dashboard()
    assert body["enabled"] is True
    assert body["read_only"] is True
    assert body["never_modifies_research"] is True
    assert body["never_changes_house_views"] is True
    assert body["never_changes_recommendations"] is True
    assert "executive_status" in body
    assert "platform_status" in body
    assert "engine_status" in body
    assert "api_status" in body
    assert "knowledge_growth" in body
    assert "coverage_dashboard" in body
    assert "company_monitor" in body
    assert "research_pipeline" in body
    assert "prediction_intelligence" in body
    assert "data_quality" in body
    assert "company_analysis" in body
    assert "academy" in body
    assert "cid" in body
    assert "system_health" in body
    assert "live_event_stream" in body
    assert "executive_copilot" in body
    assert "architecture_map" in body
    assert "alerts_centre" in body
    assert "deployment_centre" in body
    assert "performance_analytics" in body
    assert body["executive_status"]["agi_status"]
    assert len(body["platform_status"]) >= 10
    assert len(body["engine_status"]) >= 5
    assert len(body["api_status"]) >= 5


def test_architecture_map_has_nodes():
    body = dashboard()
    nodes = body["architecture_map"]["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) >= 10
    ids = {n["id"] for n in nodes}
    assert "providers" in ids
    assert "ask_agi" in ids
    assert "cid" in ids
    assert "investment_office" in ids


def test_quality_gates():
    qg = quality_gates()
    assert qg["programme"] == PROGRAMME
    assert qg["version"] == MISSION_CONTROL_VERSION
    assert qg["passed"] is True
    assert qg["criteria"]["read_only"] is True
    assert qg["criteria"]["never_mutates"] is True
    assert qg["criteria"]["architecture_map_present"] is True


def test_acknowledge_alert_is_local_only():
    result = acknowledge_alert("test-alert-1")
    assert result["ok"] is True
    assert result["acknowledged"] is True
    assert result["alert_id"] == "test-alert-1"
    desk = dashboard()
    # Acknowledgement is process-local and does not mutate research surfaces
    assert desk["never_modifies_research"] is True


def test_system_report_downloadable_shape():
    report = system_report()
    assert report["ok"] is True
    assert report["report_type"] == "mission_control_system_report"
    assert report["read_only"] is True
    assert "sections" in report
    sections = report["sections"]
    assert "platform_health" in sections
    assert "api_health" in sections
    assert "knowledge_growth" in sections
    assert "coverage" in sections
    assert "recommendations" in sections
