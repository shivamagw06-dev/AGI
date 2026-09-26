"""Continuous backfill until complete — queue, completion, maintenance transition."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    monkeypatch.setenv("KF_HD_TARGET_YEARS", "10")
    monkeypatch.setenv("KF_HD_BACKFILL_BATCH", "2")
    monkeypatch.setenv("KF_HD_BACKFILL_BATCHES_PER_CYCLE", "2")
    monkeypatch.setenv("KF_HD_BACKFILL_WORKERS", "1")
    from knowledge_factory.historical_depth import store as hd_store
    from live_data import store as lidi_store

    hd_store.reset_store()
    lidi_store.reset_runtime()
    yield
    hd_store.reset_store()
    lidi_store.reset_runtime()


def test_priority_ordering():
    from knowledge_factory.historical_depth.universe_priority import prioritised_universe, priority_tier

    assert priority_tier("INFY") == 1
    ordered = prioritised_universe(coverage_years={"INFY": 20, "ZOMATO": 1})
    # Nifty 50 names come before lower tiers
    assert ordered.index("INFY") < ordered.index("ZOMATO") if "ZOMATO" in ordered else True


def test_queue_persists_and_prioritises(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.queue.supported_universe",
        lambda: ["INFY", "TCS", "ZOMATO"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS", "ZOMATO"],
    )
    q = bf_queue.ensure_queue(force_refresh=True)
    assert len(q["companies"]) == 3
    batch = bf_queue.next_batch(batch_size=2)
    assert len(batch) == 2
    # INFY/TCS (nifty50) before ZOMATO
    assert all(b["company"] in {"INFY", "TCS"} for b in batch)


def test_enrich_marks_complete_and_maintenance(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth.backfill import run_backfill_batch
    from knowledge_factory.historical_depth.completion import evaluate_completion

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.queue.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    bf_queue.ensure_queue(force_refresh=True)
    report = run_backfill_batch(entities=["INFY", "TCS"], batch_size=2, target_years=10)
    assert report["ok"] is True
    assert report["processed"] == 2
    ev = evaluate_completion("INFY", target_years=10)
    assert ev["complete"] is True
    assert ev["hard_ok"] is True
    assert ev["hard_pct"] == 100.0
    assert ev["dimensions"]["embeddings"]["status"] == "complete"
    assert ev["dimensions"]["ohlcv"]["status"] == "complete"
    # Queue should move to maintenance
    q = bf_queue.load_queue()
    statuses = {c["company"]: c["status"] for c in q["companies"]}
    assert statuses["INFY"] == bf_queue.STATUS_MAINTENANCE
    assert statuses["TCS"] == bf_queue.STATUS_MAINTENANCE
    transition = bf_queue.maybe_transition_to_maintenance()
    assert transition["remaining"] == 0
    assert transition["engine"]["maintenance_only"] is True


def test_run_until_budget_stops_when_empty(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth.backfill import run_until_batch_budget

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.queue.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    bf_queue.ensure_queue(force_refresh=True)
    out = run_until_batch_budget(max_batches=5, batch_size=1, stop_when_empty=True)
    assert out["ok"] is True
    assert out["remaining"] == 0
    assert out["maintenance_only"] is True
    # Second call should be maintenance mode (1 light batch max)
    out2 = run_until_batch_budget(max_batches=3, batch_size=1, stop_when_empty=True)
    assert out2["mode"] == "maintenance"
    assert out2["batches_run"] <= 1


def test_cgl_historical_backfill_wrapper(monkeypatch):
    from continuous_gather_learn.historical_backfill import run_historical_backfill
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.queue.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.prioritised_universe",
        lambda **kwargs: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.coverage_reconcile.prioritised_universe",
        lambda **kwargs: ["INFY"],
    )
    bf_queue.ensure_queue(force_refresh=True)
    result = run_historical_backfill(batch_size=1, max_batches=2)
    assert result["ok"] is True
    assert result["progress"]["remaining_backlog"] == 0
    assert result["maintenance_only"] is True
