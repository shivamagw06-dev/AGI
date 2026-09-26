"""Living universe, hard/soft scores, knowledge density."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    monkeypatch.setenv("KF_HD_TARGET_YEARS", "10")
    from knowledge_factory.historical_depth import store as hd_store
    from live_data import store as lidi_store

    hd_store.reset_store()
    lidi_store.reset_runtime()
    yield
    hd_store.reset_store()
    lidi_store.reset_runtime()


def test_hard_soft_scores_and_density(monkeypatch):
    from knowledge_factory.historical_depth.backfill import run_backfill_batch
    from knowledge_factory.historical_depth.completion import company_scorecard, evaluate_completion
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY"])
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.living_universe.supported_universe",
        lambda: ["INFY"],
    )
    bf_queue.ensure_queue(force_refresh=True)
    run_backfill_batch(entities=["INFY"], batch_size=1, target_years=10)
    ev = evaluate_completion("INFY", target_years=10)
    assert ev["hard_ok"] is True
    assert ev["hard_pct"] == 100.0
    assert "soft_pct" in ev
    assert "overall_pct" in ev
    # Soft may be < 100 if artefacts missing — must not block hard
    card = company_scorecard("INFY")
    assert card["density"] in {"Excellent", "Good", "Moderate", "Thin"}
    assert card["hard_pct"] == 100.0


def test_ipo_auto_enqueues_and_reopens_maintenance(monkeypatch):
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth.backfill import run_until_batch_budget
    from knowledge_factory.historical_depth.living_universe import (
        living_universe_board,
        register_pending_ipo,
        sync_listed_universe,
    )

    universe = ["INFY"]

    def _uni():
        return list(universe)

    monkeypatch.setattr(bf_queue, "supported_universe", _uni)
    monkeypatch.setattr("knowledge_factory.historical_depth.universe_priority.supported_universe", _uni)
    monkeypatch.setattr("knowledge_factory.historical_depth.living_universe.supported_universe", _uni)

    bf_queue.ensure_queue(force_refresh=True)
    sync_listed_universe()  # bootstrap snapshot
    out = run_until_batch_budget(max_batches=3, batch_size=1)
    assert out["remaining"] == 0
    assert out["maintenance_only"] is True

    register_pending_ipo(symbol="NEWCO", name="New Co IPO")
    universe.append("NEWCO")
    board = sync_listed_universe()
    assert "NEWCO" in board["new_listings"] or "NEWCO" in board["enqueued"]
    assert board["coverage_finished"] is False
    state = bf_queue.load_engine_state()
    assert state["maintenance_only"] is False  # reopened for IPO
    q = bf_queue.load_queue()
    row = next(c for c in q["companies"] if c["company"] == "NEWCO")
    assert row["status"] == bf_queue.STATUS_PENDING
    live = living_universe_board()
    assert live["queue_ready"] is True
    assert live["pending_ipos_count"] == 0  # promoted to listed


def test_soft_missing_does_not_block_when_hard_data_verified(monkeypatch):
    from knowledge_factory.historical_depth.completion import evaluate_completion, record_attempt
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from knowledge_factory.historical_depth import store as hd_store
    from knowledge_factory.historical_depth.schema import pit_record
    from continuous_gather_learn.embeddings import embed_knowledge_extract
    from continuous_gather_learn.knowledge_extract import extract_from_hd_series

    collect_entity_history("INFY", prefer_live=False)
    extract_from_hd_series("INFY")
    embed_knowledge_extract("INFY")
    # Verified shareholding required for hard_ok (n_a no longer completes)
    hd_store.put_series(
        "shareholding",
        "INFY",
        [
            pit_record(
                entity="INFY",
                kind="shareholding",
                period="2024-03-31",
                period_end="2024-03-31",
                available_from="2024-03-31",
                payload={"promoter": 14.0, "fii": 33.0, "dii": 25.0, "mutual_funds": 12.0, "public": 16.0, "pledged": 0.0},
                source="shareholding_connector",
            )
        ],
    )
    # Soft presentations may be absent — IR docs fixture still satisfies hard ir_docs
    record_attempt("INFY", "_wave", status="complete")
    # No presentations / transcripts on purpose — soft only
    ev = evaluate_completion("INFY", target_years=10)
    assert ev["dimensions"]["ir_docs"]["status"] == "complete"
    assert ev["hard_ok"] is True
    assert ev["dimensions"]["investor_presentations"]["status"] in {"missing", "n_a"}
    assert ev["complete"] is True


def test_empty_attempt_does_not_inflate_hard_coverage(tmp_path):
    from knowledge_factory.historical_depth.completion import evaluate_completion, record_attempt
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from knowledge_factory.historical_depth import store as hd_store
    from continuous_gather_learn.embeddings import embed_knowledge_extract
    from continuous_gather_learn.knowledge_extract import extract_from_hd_series

    collect_entity_history("TCS", prefer_live=False)
    extract_from_hd_series("TCS")
    embed_knowledge_extract("TCS")
    # Remove verified shareholding — n_a attempt must not complete hard dim
    sh_path = hd_store.hd_root() / "shareholding" / "TCS.json"
    if sh_path.exists():
        sh_path.unlink()
    record_attempt("TCS", "shareholding", status="n_a")
    ev = evaluate_completion("TCS", target_years=10)
    assert ev["dimensions"]["shareholding"]["status"] != "complete"
    assert ev["hard_ok"] is False
