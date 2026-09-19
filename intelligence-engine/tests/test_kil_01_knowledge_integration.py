"""KIL-01 — Knowledge Integration Layer tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_evidence.integration.schema import (
    KIL_PHASE1_DEMO,
    KIL_VERSION,
    KIL_WORKSTREAM_ID,
    COVERAGE_STATES,
    MISSION_STATEMENT,
)
from institutional_evidence.integration.events.bus import emit_cgl_events, list_events
from institutional_evidence.integration.versioning.snapshots import (
    create_knowledge_snapshot,
    get_latest_snapshot,
)
from institutional_evidence.integration.coverage_states.states import compute_coverage_state
from institutional_evidence.integration.confidence.score import compute_knowledge_confidence
from institutional_evidence.integration.transform.kf_to_canonical import transform_company_knowledge
from institutional_evidence.integration.layer import (
    health,
    kil_status,
    integrate_cgl_run,
    integrate_company,
    get_integrated_company,
)
from institutional_evidence.integration.expansion import expansion_status
from institutional_evidence.integration import persist as kil_persist
from institutional_evidence.production import get_kil_status, soft_slice_knowledge_health
from institutional_evidence.schema import AGI_PLATFORM_VERSION, IEP_VERSION


def test_kil_identity_and_mission():
    st = kil_status()
    assert st["workstream_id"] == "KIL-01"
    assert st["status"] == "ok"
    assert st["enabled"] is True
    assert KIL_VERSION.startswith("kil-01")
    assert "Knowledge Operating System" in MISSION_STATEMENT
    assert st["pipeline"][1] == "Continuous Gather → Learn"
    assert st["pipeline"][2] == "Knowledge Integration Layer"
    assert AGI_PLATFORM_VERSION == "1.1.2-kil"
    assert IEP_VERSION == "iep-01-v1.1.2"


def test_kil_health_alias_for_agent_map():
    h = health()
    assert h["ok"] is True
    assert h["status"] == "ok"
    assert h["enabled"] is True
    assert h["workstream_id"] == "KIL-01"


def test_phase1_demo_five_companies():
    assert list(KIL_PHASE1_DEMO) == [
        "RELIANCE",
        "HDFCBANK",
        "TCS",
        "INFY",
        "ICICIBANK",
    ]


def test_emit_immutable_cgl_events():
    run = {
        "ok": True,
        "run_id": "cgl_test_1",
        "slot": "overnight",
        "volumes": {"knowledge_extracts": 2, "collectors_ok": 3},
        "phases": [{"name": "financial_backfill"}, {"name": "transcript_sync"}],
    }
    events = emit_cgl_events(run, companies_updated=["RELIANCE", "TCS"])
    assert events
    assert all(e.get("immutable") for e in events)
    types = {e["event_type"] for e in events}
    assert "KnowledgeCollected" in types
    listed = list_events(limit=10)
    assert listed["count"] >= 1


def test_knowledge_snapshot_version_label():
    snap = create_knowledge_snapshot(
        run_id="cgl_snap_1",
        slot="overnight",
        companies_updated=["RELIANCE"],
        evidence_added=2,
        financial_statements_updated=1,
        research_invalidated=["res_x"],
    )
    assert snap["immutable"] is True
    assert "overnight" in snap["knowledge_version"]
    assert get_latest_snapshot()["snapshot_id"] == snap["snapshot_id"]


def test_coverage_states_progression():
    discovered = compute_coverage_state(discovered=True)
    assert discovered["coverage_state"] == "DISCOVERED"
    ready = compute_coverage_state(
        transformed={"financials_published": True, "period_count": 8},
        quality={"publish_allowed": True},
        pack={"claim_safe": True, "research_ready": True},
        knowledge_confidence={"above_threshold": True},
    )
    assert ready["coverage_state"] == "RESEARCH READY"
    complete = compute_coverage_state(
        transformed={"financials_published": True, "period_count": 20},
        pack={"claim_safe": True, "research_ready": True},
        coverage={"institutional_coverage_complete": True},
        knowledge_confidence={"above_threshold": True},
    )
    assert complete["coverage_state"] in {
        "INSTITUTIONAL COVERAGE COMPLETE",
        "CONTINUOUS MONITORING",
    }
    assert set(COVERAGE_STATES) == set(discovered["states"])


def test_transform_and_integrate_company():
    tr = transform_company_knowledge("RELIANCE")
    assert tr["ok"] is True
    assert tr["ticker"] == "RELIANCE"
    assert "CanonicalFinancialStatements" in tr["models"]
    assert tr["rule"].startswith("Provider schemas")

    integ = integrate_company("RELIANCE", trigger_repair=False)
    assert integ["ok"] is True
    assert integ["entity_id"] == "AGI-COMPANY-0000043"
    assert "coverage_state" in integ
    assert "knowledge_confidence" in integ


def test_integrate_cgl_run_creates_snapshot_and_events():
    run = {
        "ok": True,
        "run_id": "cgl_kil_demo",
        "slot": "overnight",
        "volumes": {"knowledge_extracts": 1, "collectors_ok": 2},
        "phases": [{"name": "historical_update"}],
    }
    out = integrate_cgl_run(run, companies=["RELIANCE", "TCS"])
    assert out["ok"] is True
    assert out["snapshot"]["knowledge_version"]
    assert out["summary"]["companies"] == 2
    assert out["events"]
    # Persisted so HTTP Mission Control can see gather-sidecar integrations
    assert kil_persist.get_company("RELIANCE") is not None
    assert kil_persist.get_latest_snapshot() is not None
    assert health()["companies_integrated"] >= 2
    # Simulate cold HTTP process cache
    from institutional_evidence.integration import layer as kil_layer

    kil_layer._COMPANY_STATE.clear()
    assert get_integrated_company("TCS") is not None
    assert get_integrated_company("TCS")["ticker"] == "TCS"


def test_knowledge_confidence_structure():
    kc = compute_knowledge_confidence(
        "RELIANCE",
        transformed={
            "models": {
                "CanonicalFinancialStatements": {
                    "periods": [{"period_type": "annual"}] * 5,
                    "published": True,
                }
            }
        },
        pack={"evidence": {"registry": {"items": [{"freshness_ok": True, "hash": "a"}]}}},
        timeline={"event_count": 5},
    )
    assert "knowledge_confidence" in kc
    assert "financial_coverage" in kc["components"]


def test_expansion_locked_until_top20_complete():
    st = expansion_status(top20_complete_count=0, top20_total=20)
    assert st["unlocked"] is False
    assert st["next_universe"] == "nifty_500"
    assert st["next_size"] == 500
    unlocked = expansion_status(top20_complete_count=20, top20_total=20)
    assert unlocked["unlocked"] is True


def test_production_kil_soft_slice():
    st = get_kil_status()
    assert st["workstream_id"] == KIL_WORKSTREAM_ID
    assert st.get("status") == "ok"
    slice_ = soft_slice_knowledge_health()
    assert slice_["board"] == "Knowledge Health"
    assert slice_["status"] == "ok"


def test_knowledge_health_board_uses_cache_not_live_integrate():
    from institutional_evidence.integration.health.dashboard import knowledge_health_board

    integrate_company("INFY", trigger_repair=False)
    board = knowledge_health_board(demo_only=True, live_integrate=False)
    assert board["ok"] is True
    rows = {r["ticker"]: r for r in board["companies"] if r.get("ticker")}
    assert "INFY" in rows
    assert rows["INFY"].get("coverage_state") not in {None, "PENDING_INTEGRATION"}


def test_agent_map_marks_kil_working():
    from mission_control.agent_map import build_agent_map

    am = build_agent_map()
    kil = next(a for a in am["agents"] if a["id"] == "knowledge_integration_layer")
    assert kil["status"] == "working"
    assert kil["name"].startswith("Knowledge Integration Layer")
