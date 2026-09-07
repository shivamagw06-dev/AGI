"""L-01 — Launch Phase tests (usage validation, not feature expansion)."""

from __future__ import annotations

import pytest

from institutional_launch.analytics.journey import journey_funnel, record_journey_step
from institutional_launch.feature_flags.registry import get_flag, list_flags, set_flag
from institutional_launch.feedback.engine import feedback_summary, submit_feedback
from institutional_launch.production import (
    feedback_submit_api,
    flags_api,
    funnel_api,
    health,
    metrics_api,
    report_api,
    reset_for_tests,
    sla_api,
    soft_slice_mission_control,
    track_journey,
)
from institutional_launch.product_metrics.adoption import product_dashboard, record_ask
from institutional_launch.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    JOURNEY_STAGES,
    L_WORKSTREAM_ID,
    SLA_TARGETS,
    V11_FEATURE_FLAGS,
)
from institutional_launch.sla.targets import evaluate_slas


@pytest.fixture(autouse=True)
def _clean():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_is_usage_validation_not_expansion():
    h = health()
    assert h["workstream_id"] == L_WORKSTREAM_ID
    assert h["is_usage_validation"] is True
    assert h["is_feature_expansion"] is False
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True


def test_journey_funnel_stages():
    for stage in JOURNEY_STAGES:
        record_journey_step(stage, user_id="analyst.demo", ok=True, duration_ms=12)
    funnel = journey_funnel()
    assert funnel["stages"] == list(JOURNEY_STAGES)
    assert len(funnel["funnel"]) == len(JOURNEY_STAGES)
    assert funnel["funnel"][0]["completions"] >= 1


def test_adoption_and_ask_metrics():
    record_ask(ok=True, latency_ms=120, sources=3)
    record_ask(ok=False, latency_ms=400, sources=0)
    dash = product_dashboard()
    assert dash["ask_agi"]["questions_day"] == 2
    assert dash["ask_agi"]["successful_completions"] == 1
    assert dash["ask_agi"]["median_response_ms"] is not None
    assert dash["adoption"]["daily_active_users"] >= 0


def test_feedback_engine_and_backlog():
    ok = submit_feedback(
        screen="ask_agi",
        reaction="helpful",
        user_id="pm.demo",
    )
    assert ok["ok"] is True
    bad = submit_feedback(
        screen="ask_agi",
        reaction="not_helpful",
        comment="too slow and missing data",
        user_id="pm.demo",
    )
    assert bad["ok"] is True
    assert "too_slow" in bad["tags"] or "missing_data" in bad["tags"]
    assert bad["backlog_candidate"] is True
    summary = feedback_summary()
    assert summary["total"] == 2
    assert summary["helpful"] == 1
    assert summary["not_helpful"] == 1


def test_finance_answer_feedback_tags_are_structured():
    row = submit_feedback(
        screen="ask_agi",
        reaction="not_helpful",
        tags=["wrong_entity", "missing_evidence", "not_an_allowed_tag"],
    )
    assert row["ok"] is True
    assert row["tags"] == ["wrong_entity", "missing_evidence"]


def test_v11_feature_flags_default_off():
    flags = list_flags()
    assert flags["all_disabled"] is True
    for name in V11_FEATURE_FLAGS:
        assert get_flag(name) is False
    set_flag("COLLABORATION", True, actor="admin.demo")
    assert get_flag("COLLABORATION") is True
    assert list_flags()["all_disabled"] is False


def test_sla_targets_and_evaluation():
    assert SLA_TARGETS["ask_agi_p95_latency_ms"] == 3000
    record_ask(ok=True, latency_ms=100)
    slas = evaluate_slas(
        ask_p95_ms=100,
        data_freshness_minutes=10,
        availability_pct=99.95,
        architecture_conformance_pct=100,
        publication_success_pct=100,
    )
    assert slas["breach_count"] == 0
    assert slas["all_met"] is True
    breach = evaluate_slas(ask_p95_ms=5000, architecture_conformance_pct=100)
    assert any(b["metric"] == "ask_agi_p95_latency_ms" for b in breach["breaches"])


def test_launch_center_soft_slice():
    board = soft_slice_mission_control()
    assert board["launch_center"] is True
    assert board["is_usage_validation"] is True
    assert "daily_active_users" in board


def test_apis_metrics_funnel_flags_sla_report():
    track_journey({"stage": "login", "user_id": "cio.demo", "ok": True})
    track_journey({"stage": "ask_agi", "user_id": "cio.demo", "ok": True, "duration_ms": 80})
    feedback_submit_api({"screen": "workspace", "reaction": "👍", "user_id": "cio.demo"})
    m = metrics_api()
    assert m["ok"] is True
    assert funnel_api()["ok"] is True
    assert flags_api()["all_disabled"] is True
    assert sla_api()["ok"] is True
    report = report_api()
    assert report["ok"] is True
    assert "ready_for_v11" in report["report"]
    assert report["report"]["architecture_frozen"] is True


def test_soft_hook_ask_increments_metrics():
    from institutional_orchestrator.production import ask, reset_for_tests as reset_uag

    reset_uag()
    before = product_dashboard()["ask_agi"]["questions_day"]
    ask(
        {
            "question": "What is the view on TCS?",
            "bypass_cache": True,
            "_prp_security_bypass": True,
            "user_id": "analyst.demo",
        }
    )
    after = product_dashboard()["ask_agi"]["questions_day"]
    assert after >= before + 1


def test_ready_for_v11_requires_usage_evidence():
    # Fresh state — no usage → not ready
    report = report_api()["report"]
    assert report["has_usage_evidence"] is False
    assert report["ready_for_v11"] is False
    # With usage + green SLAs
    track_journey({"stage": "login", "user_id": "analyst.demo", "ok": True})
    record_ask(ok=True, latency_ms=50, sources=2)
    report2 = report_api()["report"]
    assert report2["has_usage_evidence"] is True
