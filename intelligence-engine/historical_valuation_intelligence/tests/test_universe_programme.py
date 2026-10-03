"""HVIE Universe Completion Programme — queue, eligibility, pipeline stages."""

from __future__ import annotations

from historical_valuation_intelligence.universe_programme import queue, pipeline
from historical_valuation_intelligence.universe_programme.models import (
    LIFE_COMPLETE,
    LIFE_READY,
    LIFE_WAITING_PRICE,
    QUEUE_COMPLETED,
    QUEUE_PENDING,
    QUEUE_SKIPPED,
)


class FakeStore:
    MAX_LIMIT = 5000

    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "company_master": [
                {"symbol": "AAA", "sector": "IT", "industry": "Software"},
                {"symbol": "BBB", "sector": "Banks", "industry": "Private Banks"},
                {"symbol": "CCC", "sector": "IT", "industry": "Software"},
            ],
            "hvie_universe_queue": [],
            "daily_market_history": [],
            "financials_annual": [],
            "financials_quarterly": [],
            "corporate_actions": [],
            "hvie_company_state": [],
            "historical_valuation": [],
            "historical_statistics": [],
            "research_timeline": [],
        }

    def fetch(self, tab_id, limit=200, offset=0, filters=None, entity=None, **_kwargs):
        rows = list(self.tables.get(tab_id) or [])
        if filters:
            for k, v in filters.items():
                rows = [r for r in rows if r.get(k) == v]
        if entity:
            ent = str(entity).upper()
            rows = [r for r in rows if str(r.get("symbol") or "").upper() == ent]
        total = len(rows)
        page = rows[offset: offset + limit]
        return {"ok": True, "rows": page, "total": total, "limit": limit, "offset": offset}

    def all_rows(self, tab_id, entity=None, limit=5000, **_kwargs):
        return self.fetch(tab_id, limit=min(limit, self.MAX_LIMIT), entity=entity)["rows"]

    def entities(self, tab_id):
        return sorted({str(r.get("symbol")).upper() for r in self.tables.get(tab_id) or [] if r.get("symbol")})


class FakeGateway:
    def __init__(self, store: FakeStore):
        self.store = store

    def write(self, tab_id, rows, **_kwargs):
        table = self.store.tables.setdefault(tab_id, [])
        for row in rows:
            key = str(row.get("symbol") or "")
            if tab_id == "hvie_universe_queue":
                idx = next((i for i, r in enumerate(table) if r.get("symbol") == key), None)
                if idx is None:
                    table.append(dict(row))
                else:
                    table[idx] = {**table[idx], **row}
            else:
                table.append(dict(row))
        return {"ok": True, "written": len(rows)}


def _patch_warehouse(monkeypatch, store: FakeStore):
    import institutional_warehouse as wh
    import institutional_warehouse.gateway as gateway_mod

    gw = FakeGateway(store)
    monkeypatch.setattr(wh, "store", store)
    monkeypatch.setattr(wh, "gateway", gw)
    monkeypatch.setattr(gateway_mod, "write", gw.write)


def test_sync_universe_classifies_all_masters(monkeypatch):
    store = FakeStore()
    _patch_warehouse(monkeypatch, store)

    out = queue.sync_universe()
    assert out["universe"] == 3
    assert out["created"] == 3
    rows = queue.all_queue_rows()
    assert len(rows) == 3
    assert all(r.get("queue_status") == QUEUE_PENDING for r in rows)
    assert all(r.get("lifecycle") == "NOT_STARTED" for r in rows)


def test_sync_recovers_running_after_restart(monkeypatch):
    store = FakeStore()
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe(adopt_existing=False)
    # Stale RUNNING (no last_run_at) is recovered; fresh RUNNING is left alone.
    queue.upsert_queue_row("AAA", queue_status="RUNNING", lifecycle="RUNNING", last_run_at=None)
    out = queue.sync_universe(adopt_existing=False)
    assert out["recovered_running"] >= 1
    row = queue.get_queue_row("AAA")
    assert row["queue_status"] == "RETRY"


def test_import_existing_hvie_progress(monkeypatch):
    store = FakeStore()
    store.tables["hvie_company_state"] = [
        {
            "symbol": "AAA",
            "seeded": True,
            "status": "SEEDED",
            "observations": 40,
            "last_percentile": 55.0,
            "last_regime": "FAIR",
            "primary_metric": "pe",
        }
    ]
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe(adopt_existing=False)
    out = queue.import_existing_hvie_progress()
    assert out["adopted"] == 1
    row = queue.get_queue_row("AAA")
    assert row["queue_status"] == QUEUE_COMPLETED
    assert row["lifecycle"] == LIFE_COMPLETE
    assert row["has_percentile"] is True


def test_process_company_adopts_seeded_state(monkeypatch):
    store = FakeStore()
    store.tables["hvie_company_state"] = [
        {
            "symbol": "AAA",
            "seeded": True,
            "status": "SEEDED",
            "observations": 40,
            "last_percentile": 33.0,
            "last_regime": "CHEAP",
        }
    ]
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe(adopt_existing=False)
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime._get_state",
        lambda symbol: store.tables["hvie_company_state"][0],
    )
    out = pipeline.process_company("AAA")
    assert out["ok"] is True
    assert out.get("adopted") is True
    assert out["queue_status"] == QUEUE_COMPLETED


def test_classify_waiting_price(monkeypatch):
    store = FakeStore()
    _patch_warehouse(monkeypatch, store)
    from historical_valuation_intelligence.universe_programme.eligibility import classify_company

    out = classify_company("AAA")
    assert out["eligible"] is False
    assert out["lifecycle"] == LIFE_WAITING_PRICE


def test_classify_waiting_share_count(monkeypatch):
    store = FakeStore()
    store.tables["daily_market_history"] = [
        {"symbol": "AAA", "date": f"2024-01-{i:02d}", "close": 100 + i}
        for i in range(1, 20)
    ]
    store.tables["financials_annual"] = [
        {"symbol": "AAA", "fiscal_year": "FY24", "pat": 1000, "equity": 5000},
    ]
    _patch_warehouse(monkeypatch, store)
    from historical_valuation_intelligence.universe_programme.eligibility import classify_company
    from historical_valuation_intelligence.universe_programme.models import LIFE_WAITING_SHARE_COUNT

    out = classify_company("AAA")
    assert out["eligible"] is False
    assert out["lifecycle"] == LIFE_WAITING_SHARE_COUNT
    assert out["blocking_reason"] == "missing_share_count"


def test_process_company_skips_when_waiting_inputs(monkeypatch):
    store = FakeStore()
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe()
    out = pipeline.process_company("AAA")
    assert out["queue_status"] == QUEUE_SKIPPED
    assert out["lifecycle"] == LIFE_WAITING_PRICE
    row = queue.get_queue_row("AAA")
    assert row["queue_status"] == QUEUE_SKIPPED


def test_process_company_completes_pipeline(monkeypatch):
    store = FakeStore()
    # Enough price + statement history for eligibility.
    store.tables["daily_market_history"] = [
        {"symbol": "AAA", "date": f"2024-01-{i:02d}", "close": 100 + i}
        for i in range(1, 20)
    ]
    store.tables["financials_annual"] = [
        {"symbol": "AAA", "fiscal_year": "FY24", "pat": 1000, "equity": 5000, "shares_outstanding": 100},
    ]
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe()

    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime.bootstrap_company",
        lambda symbol, cadence="monthly": {
            "ok": True,
            "symbol": symbol,
            "action": "bootstrap",
            "observations": 40,
            "first": "2020-01-01",
            "last": "2026-08-01",
        },
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.compute.ensure_history",
        lambda symbol, **kw: {"ok": True, "observations": 40, "action": "skip"},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.persist.persist_company_statistics",
        lambda symbol, metrics=None: {"ok": True, "rows": 5},
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.engine.company_pack",
        lambda symbol, metric="pe", window="max": {
            "ok": True,
            "historical_percentile": 42.0,
            "regime": "FAIR",
            "current": 22.0,
            "median": 20.0,
            "coverage": {"observation_count": 40, "first": "2020-01-01", "last": "2026-08-01"},
        },
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.research_triggers.emit_research_events",
        lambda *a, **k: [{"event": "valuation_crossed_median"}],
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime._upsert_state",
        lambda symbol, **fields: None,
    )
    monkeypatch.setattr(
        "historical_valuation_intelligence.runtime._get_state",
        lambda symbol: {"observations": 40, "seeded": True},
    )

    out = pipeline.process_company("AAA")
    assert out["ok"] is True
    assert out["queue_status"] == QUEUE_COMPLETED
    assert out["lifecycle"] == LIFE_COMPLETE
    row = queue.get_queue_row("AAA")
    assert row["has_percentile"] is True
    assert row["has_regime"] is True
    assert row["has_bands"] is True
    assert row["stage"] == "complete"


def test_pipeline_counts(monkeypatch):
    store = FakeStore()
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe(adopt_existing=False)
    queue.upsert_queue_row(
        "AAA",
        queue_status=QUEUE_COMPLETED,
        lifecycle=LIFE_COMPLETE,
        eligible=True,
        has_percentile=True,
        has_bands=True,
        has_regime=True,
        has_statistics=True,
        has_research=True,
        observations=40,
    )
    queue.upsert_queue_row("BBB", queue_status=QUEUE_PENDING, lifecycle=LIFE_READY, eligible=True)
    counts = queue.pipeline_counts()
    assert counts["universe"] == 3
    assert counts["complete"] == 1
    assert counts["percentiles"] == 1
    assert counts["pending"] == 2


def test_board_payload_shape(monkeypatch):
    from historical_valuation_intelligence.universe_programme import runtime as univ_rt

    store = FakeStore()
    _patch_warehouse(monkeypatch, store)
    queue.sync_universe(adopt_existing=False)
    board = univ_rt.board()
    assert board["ok"] is True
    assert "plain_english" in board
    assert "progress" in board
    assert "stages" in board
    assert isinstance(board["failures"], list)
