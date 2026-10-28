"""Track 3 — Institutional Research Office acceptance tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from research_office import store
from research_office.office.runner import run_after_scheduler_ready, run_morning_desk
from research_office.production import company, dashboard, health, history, publications, queue, watchlists
from research_office.publications.registry import get_replay
from research_office.schema import FORBIDDEN_CLAIMS, FREEZE_LOCKS, PUBLICATION_TYPES


def setup_function() -> None:
    store.reset()


def test_health_and_freeze() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["knowledge_only"] is True
    assert h["no_recommendations"] is True
    assert FREEZE_LOCKS["phases_1_7"] is True
    assert FREEZE_LOCKS["institutional_scheduler"] is True


def test_morning_publications_and_registry() -> None:
    out = run_morning_desk(force=True, company_triggers=["INFY"])
    assert out["status"] == "ok"
    types = {p["publication_type"] for p in out["publications"]}
    for required in (
        "market_morning_brief",
        "macro_intelligence_brief",
        "government_intelligence_brief",
        "sector_intelligence_report",
        "industry_intelligence_report",
        "corporate_events_report",
        "alternative_data_report",
        "market_expectations_report",
        "company_research_note",
    ):
        assert required in types

    pubs = publications(limit=50)["publications"]
    assert len(pubs) >= 9
    for p in pubs:
        assert p.get("recommendation") is None
        assert p.get("knowledge_version")
        assert p.get("evidence_version")
        assert p.get("historical_replay", {}).get("replay_id")
        assert p.get("sources")
        assert (p.get("validation") or {}).get("provenance_ok") is True
        blob = json.dumps(p.get("body") or {}, default=str).lower()
        for claim in FORBIDDEN_CLAIMS:
            if claim == "buy":
                assert " buy " not in f" {blob} "
                assert '"buy"' not in blob
            else:
                assert claim not in blob
        replay = get_replay(p["historical_replay"]["replay_id"])
        assert replay and replay.get("found") is True
        assert replay.get("point_in_time") is True


def test_watchlists_and_queue_and_dashboard() -> None:
    run_morning_desk(force=True, company_triggers=["INFY"])
    wl = watchlists()["watchlists"]
    assert "research" in wl
    assert "corporate_events" in wl
    assert "expectation" in wl
    q = queue()["queue"]
    assert "todays_missing_evidence" in q
    assert "todays_companies" in q
    assert q.get("recommendation") is None
    dash = dashboard()
    assert dash["north_star"] == "morning_research_ready_for_users"
    assert dash.get("todays_publications")
    assert history(limit=5)["n"] >= 1


def test_company_note_api() -> None:
    out = company("INFY", generate=True)
    assert out["ticker"] == "INFY"
    assert out["n"] >= 1
    assert out["recommendation"] is None
    note = out["notes"][0]
    assert "transparent_insufficiency" in (note.get("body") or {}).get("sections", {})


def test_scheduler_soft_wire_gate() -> None:
    skipped = run_after_scheduler_ready({"system_ready": False, "state": "FAILED"})
    assert skipped["status"] == "skipped"
    ran = run_after_scheduler_ready({"system_ready": True, "run_id": "morn_test"})
    assert ran["status"] == "ok"
    assert ran.get("scheduler_run_id") == "morn_test"


def test_frozen_surfaces_untouched() -> None:
    root = Path(__file__).resolve().parents[2]
    for rel in (
        "institutional_reasoning/execution_governance.py",
        "knowledge_factory/schedulers/daily.py",
        "ask_pipeline/pipeline.py",
        "decision_quality/pipeline.py",
    ):
        path = root / rel
        assert path.exists()
        ast.parse(path.read_text(encoding="utf-8"))
    runner = (root / "research_office" / "office" / "runner.py").read_text(encoding="utf-8")
    assert "govern_answer" not in runner
    assert "decide_portfolio" not in runner
    assert "BUY" not in runner


def test_publication_types_catalog() -> None:
    assert "market_morning_brief" in PUBLICATION_TYPES
    assert len(PUBLICATION_TYPES) >= 9
