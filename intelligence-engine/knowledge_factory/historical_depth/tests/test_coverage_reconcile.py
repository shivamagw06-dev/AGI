"""Coverage-derived backlog — maintenance gated on verified data plane."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path / "kip"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    monkeypatch.setenv("KF_HD_FIXTURE_QUARTERLY", "true")
    monkeypatch.setenv("APP_ENV", "test")
    from knowledge_factory.historical_depth import store as hd_store
    from live_data import store as lidi_store

    hd_store.reset_store()
    lidi_store.reset_runtime()
    yield
    hd_store.reset_store()
    lidi_store.reset_runtime()


def test_reconcile_reopens_false_maintenance(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth.coverage_reconcile import reconcile_universe

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.prioritised_universe",
        lambda **kwargs: ["INFY", "TCS"],
    )
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY", "TCS"])

    bf_queue.ensure_queue(force_refresh=True)
    # Fake control-plane "complete"
    q = bf_queue.load_queue()
    for row in q["companies"]:
        row["status"] = bf_queue.STATUS_MAINTENANCE
        row["mode"] = "maintenance"
    bf_queue.save_queue(q)
    bf_queue.save_engine_state(
        {
            "mode": "maintenance",
            "maintenance_only": True,
            "deep_backfill_enabled": False,
        }
    )

    report = reconcile_universe(entities=["INFY", "TCS"], enqueue=True)
    assert report["maintenance_allowed"] is False
    assert report["incomplete"] >= 1
    assert report["authority"] == "evidence_based_completion"
    assert "evidence_backlog" in report
    state = bf_queue.load_engine_state()
    assert state["maintenance_only"] is False
    assert state["mode"] == "deep_backfill"
    q2 = bf_queue.load_queue()
    pending = [c for c in q2["companies"] if c["status"] == bf_queue.STATUS_PENDING]
    assert len(pending) >= 1


def test_empty_queue_alone_does_not_enter_maintenance(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.prioritised_universe",
        lambda **kwargs: ["INFY"],
    )
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY"])
    bf_queue.ensure_queue(force_refresh=True)
    # Mark queue empty (all maintenance) without data
    q = bf_queue.load_queue()
    for row in q["companies"]:
        row["status"] = bf_queue.STATUS_MAINTENANCE
    bf_queue.save_queue(q)

    out = bf_queue.maybe_transition_to_maintenance()
    assert out.get("verified_gate") is False or out.get("reopened") is True or not out.get("transitioned")
    state = bf_queue.load_engine_state()
    assert state.get("maintenance_only") is not True


def test_backlog_stats_prefer_verified_coverage(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth import store as hd_store

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY"])
    bf_queue.ensure_queue(force_refresh=True)
    q = bf_queue.load_queue()
    for row in q["companies"]:
        row["status"] = bf_queue.STATUS_MAINTENANCE
    bf_queue.save_queue(q)

    hd_store.put_report(
        "coverage_reconciliation",
        {
            "incomplete": 1,
            "verified_complete": 0,
            "universe_scanned": 1,
            "verified_hard_coverage_pct": 3.8,
            "average_history_years": 1.1,
            "dataset_coverage": {"ohlcv_pct": 3.8, "financials_pct": 0.0, "shareholding_pct": 0.0},
            "maintenance_allowed": False,
            "authority": "evidence_based_completion",
        },
    )
    stats = bf_queue.backlog_stats()
    assert stats["authority"] == "evidence_based_completion"
    assert stats["coverage_pct"] == 3.8
    assert stats["remaining"] == 1
    assert stats["fully_backfilled"] == 0


def test_evidence_based_completion_explains_backlog(monkeypatch):
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from knowledge_factory.historical_depth.completion import evidence_based_completion
    from knowledge_factory.historical_depth import store as hd_store
    from continuous_gather_learn.embeddings import embed_knowledge_extract
    from continuous_gather_learn.knowledge_extract import extract_from_hd_series

    collect_entity_history("RELIANCE", prefer_live=False)
    extract_from_hd_series("RELIANCE")
    embed_knowledge_extract("RELIANCE")
    # Remove shareholding → incomplete with explainable why
    sh_path = hd_store.hd_root() / "shareholding" / "RELIANCE.json"
    if sh_path.exists():
        sh_path.unlink()

    card = evidence_based_completion("RELIANCE", target_years=10)
    assert card["complete"] is False
    assert "shareholding" in card["missing"]
    assert "Shareholding" in (card["missing_labels"] or [])
    assert card["why_incomplete"] and "Shareholding" in card["why_incomplete"]
    assert card["hard_coverage_pct"] < 100
    marks = {c["label"]: c["mark"] for c in card["checklist"]}
    assert marks["OHLCV"] == "✓"
    assert marks["Shareholding"] == "✗"
    assert marks["IR Docs"] == "✓"
