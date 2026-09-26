"""ORCH-001 — run ledger + DAG load + duplicate trigger lock."""

from __future__ import annotations

from app.orch.ledger import OrchLedger


def test_dag_loads_expected_version_and_critical_nodes():
    ledger = OrchLedger()
    assert ledger.dag_version == "orch-1.0.0"
    nodes = set(ledger.dag_node_ids())
    for required in (
        "E01_MACRO",
        "E14_FIRM_PRIOR",
        "E03_XS",
        "L4_COMPOSITE",
        "E10_PORTFOLIO",
        "E14_ASSESS",
    ):
        assert required in nodes


def test_trigger_and_complete_dry_run():
    ledger = OrchLedger()
    run = ledger.trigger("daily_eod", as_of="2026-07-24", trigger_reason="unit_test")
    assert run.status == "running"
    ledger.complete_node(
        run.run_id,
        "E01_MACRO",
        "succeeded",
        latency_ms=1200,
        output_hash="sha256:" + ("a" * 64),
    )
    finished = ledger.finish(run.run_id, "succeeded")
    assert finished.status == "succeeded"
    assert finished.finished_at is not None
    assert "E01_MACRO" in finished.nodes


def test_duplicate_trigger_returns_already_running():
    ledger = OrchLedger()
    first = ledger.trigger("daily_eod", trigger_reason="first")
    second = ledger.trigger("daily_eod", trigger_reason="second")
    assert first.status == "running"
    assert second.status == "already_running"
    assert second.run_id == first.run_id
    ledger.finish(first.run_id, "succeeded")
    third = ledger.trigger("daily_eod", trigger_reason="after_finish")
    assert third.status == "running"
    assert third.run_id != first.run_id


def test_unknown_node_rejected():
    ledger = OrchLedger()
    run = ledger.trigger("on_demand_symbol", allow_parallel=True)
    try:
        ledger.complete_node(run.run_id, "NOT_A_NODE", "succeeded")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_status_summary():
    ledger = OrchLedger()
    summary = ledger.status_summary()
    assert summary["ok"] is True
    assert summary["document_id"] == "ORCH"
    assert summary["dag_version"] == "orch-1.0.0"
