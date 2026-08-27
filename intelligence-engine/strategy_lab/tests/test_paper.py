from strategy_lab.paper import _max_drawdown, board, capture
from institutional_warehouse import store


def test_paper_tabs_are_forward_entity_ledgers():
    snapshots = store.get_tab("strategy_paper_snapshots")
    outcomes = store.get_tab("strategy_paper_outcomes")
    assert snapshots.mode == "append"
    assert outcomes.mode == "append"
    assert snapshots.entity_column == "ticker"
    assert outcomes.entity_column == "ticker"


def test_paper_drawdown_uses_compounded_forward_returns():
    assert _max_drawdown([10.0, -10.0]) == -10.0
    assert _max_drawdown([]) is None


def test_capture_does_not_revise_frozen_signal(monkeypatch):
    writes = []
    monkeypatch.setattr(store, "all_rows", lambda *_args, **_kwargs: [
        {"strategy_id": "momentum", "signal_as_of": "2026-08-14", "ticker": "ABC"}
    ])
    from institutional_warehouse import gateway
    monkeypatch.setattr(gateway, "write", lambda *_args, **_kwargs: writes.append(_kwargs) or {"ok": True, "written": 1})
    result = capture([{
        "strategy_id": "momentum", "calculator_available": True, "version": "v1",
        "signals": [{"ticker": "ABC", "signal_session": "2026-08-14", "entry": 100, "research_direction": "LONG"}],
    }])
    assert result["eligible"] == 0
    assert result["written"] == 0
    assert writes == []


def test_paper_board_is_read_only_and_fail_closed(monkeypatch):
    monkeypatch.setattr(store, "all_rows", lambda tab, **_kwargs: [{
        "strategy_id": "time_series_momentum",
        "signal_as_of": "2026-08-14",
        "ticker": "ABC",
        "horizon_sessions": 21,
    }] if tab == "strategy_paper_snapshots" else [])

    result = board()

    momentum = result["strategies"]["time_series_momentum"]
    assert result["execution_eligible"] is False
    assert momentum["snapshots"] == 1
    assert momentum["pending_outcomes"] == 1
    assert momentum["validation_status"] == "ACCUMULATING"
