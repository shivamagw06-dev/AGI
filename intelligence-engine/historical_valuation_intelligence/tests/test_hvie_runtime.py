"""HVIE Continuous Runtime contract tests."""

from __future__ import annotations

from historical_valuation_intelligence import health, runtime_status
from historical_valuation_intelligence.runtime import (
    bootstrap_company,
    daily_append_company,
    run_bootstrap_slice,
    run_daily_append,
    run_monthly_health,
    run_once,
    run_weekly_stats,
)
from historical_valuation_intelligence.research_triggers import emit_research_events


class _FakeGateway:
    def __init__(self):
        self.writes = []

    def write(self, tab, rows, **kwargs):
        self.writes.append({"tab": tab, "rows": rows, **kwargs})
        return {"ok": True, "written": len(rows)}


def test_health_exposes_runtime_contract():
    h = health()
    assert h["ok"] is True
    assert h["role"] == "continuous_historical_valuation_service"
    assert "runtime" in h["endpoints"][-1] or any("runtime" in e for e in h["endpoints"])


def test_runtime_status_shape():
    st = runtime_status()
    assert st["ok"] is True
    assert "schedules" in st
    assert "daily" in st["schedules"]
    assert st["runtime"]["status"] in {"idle", "running", "stopped"}


def test_bootstrap_skips_when_seeded(monkeypatch):
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime._get_state",
        lambda symbol: {"seeded": True, "status": "SEEDED", "observations": 100},
    )
    out = bootstrap_company("INFY")
    assert out["action"] == "skip"
    assert out["reason"] == "already_seeded"


def test_bootstrap_seeds_and_marks_state(monkeypatch):
    states = {}

    def upsert(symbol, **fields):
        states[symbol] = {**states.get(symbol, {}), "symbol": symbol, **fields}

    monkeypatch.setattr("historical_valuation_intelligence.runtime._get_state", lambda s: states.get(s, {}))
    monkeypatch.setattr("historical_valuation_intelligence.runtime._upsert_state", upsert)
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime._policy_metric",
        lambda s: ("pe", "PE"),
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.compute.reconstruct",
        lambda symbol, **kw: {
            "ok": True,
            "symbol": symbol,
            "observations": 120,
            "first": "2010-01-15",
            "last": "2026-08-04",
        },
    )
    out = bootstrap_company("INFY", cadence="monthly")
    assert out["ok"] is True
    assert out["status"] == "SEEDED"
    assert states["INFY"]["seeded"] is True
    assert states["INFY"]["observations"] == 120


def test_daily_append_emits_research_on_regime_change(monkeypatch):
    states = {
        "INFY": {
            "seeded": True,
            "status": "SEEDED",
            "primary_metric": "pe",
            "last_regime": "FAIR",
            "observations": 80,
        }
    }
    events_called = {}

    def upsert(symbol, **fields):
        states[symbol] = {**states.get(symbol, {}), **fields}

    monkeypatch.setattr("historical_valuation_intelligence.runtime._get_state", lambda s: states.get(s, {}))
    monkeypatch.setattr("historical_valuation_intelligence.runtime._upsert_state", upsert)
    monkeypatch.setattr(
        "historical_valuation_intelligence.compute.incremental_price_update",
        lambda symbol, **kw: {"ok": True, "symbol": symbol, "observations": 1},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.engine.company_pack",
        lambda symbol, metric=None, window="max": {
            "ok": True,
            "current": 28.0,
            "median": 22.0,
            "historical_percentile": 92.0,
            "regime": "VERY_EXPENSIVE",
            "coverage": {"last": "2026-08-04", "observation_count": 81},
        },
    )

    def fake_emit(*args, **kwargs):
        events_called["kwargs"] = kwargs
        return [{"event": "valuation_highest_decile"}]

    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.emit_research_events",
        fake_emit,
    )
    out = daily_append_company("INFY")
    assert out["mode"] == "daily"
    assert out["research_events"] == 1
    assert events_called["kwargs"]["current_percentile"] == 92.0
    assert states["INFY"]["last_regime"] == "VERY_EXPENSIVE"


def test_run_once_modes(monkeypatch):
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.run_bootstrap_slice",
        lambda **kw: {"ok": True, "mode": "bootstrap", "attempted": 2},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.run_daily_append",
        lambda **kw: {"ok": True, "mode": "daily", "attempted": 3},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.run_weekly_stats",
        lambda **kw: {"ok": True, "mode": "weekly", "companies": 4},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.run_monthly_health",
        lambda: {"ok": True, "mode": "monthly", "repaired": 1},
    )
    assert run_once("bootstrap")["mode"] == "bootstrap"
    assert run_once("daily")["mode"] == "daily"
    assert run_once("weekly")["mode"] == "weekly"
    assert run_once("monthly")["mode"] == "monthly"


def test_research_triggers_write_timeline(monkeypatch):
    gw = _FakeGateway()
    monkeypatch.setattr(
        "institutional_warehouse.gateway.write",
        gw.write,
    )
    # Import path used inside emit
    import institutional_warehouse.gateway as gateway_mod

    monkeypatch.setattr(gateway_mod, "write", gw.write)

    written = emit_research_events(
        "INFY",
        metric="pe",
        current_percentile=95,
        previous_regime="FAIR",
        current_regime="VERY_EXPENSIVE",
        current_value=30,
        median=22,
    )
    assert written
    assert any("highest_decile" in (e.get("event") or "") for e in written)


def test_statement_hook_triggers_forward(monkeypatch):
    from historical_valuation_intelligence import hooks

    called = []

    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.forward_rebuild_company",
        lambda symbol, release_date=None, as_of=None, **_kw: called.append(symbol)
        or {"ok": True, "symbol": symbol},
    )
    out = hooks.after_statements_written(
        [{"symbol": "INFY", "period_end": "2026-06-30"}, {"symbol": "TCS"}]
    )
    assert out["ok"] is True
    assert out["triggered"] == 2
    assert called == ["INFY", "TCS"]


def test_ca_hook_skips_dividends(monkeypatch):
    from historical_valuation_intelligence import hooks

    called = []
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.corporate_action_rebuild",
        lambda symbol: called.append(symbol) or {"ok": True, "symbol": symbol},
    )
    out = hooks.after_corporate_actions_written(
        [
            {"symbol": "INFY", "action_type": "dividend"},
            {"symbol": "TCS", "action_type": "split"},
            {"symbol": "WIPRO", "action_type": "bonus"},
        ]
    )
    assert out["triggered"] == 2
    assert called == ["TCS", "WIPRO"]
