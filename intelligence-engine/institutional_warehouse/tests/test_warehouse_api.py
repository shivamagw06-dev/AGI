"""HTTP surface, permissions, refresh pipeline and the daily scheduler."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_api_"))

from institutional_warehouse import db, permissions, production, refresh, scheduler, store  # noqa: E402
from institutional_warehouse.schema import TABS  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    for key in ("WAREHOUSE_READERS", "WAREHOUSE_EDITORS", "WAREHOUSE_APPROVERS",
                "WAREHOUSE_PUBLISHERS", "WAREHOUSE_DEFAULT_ROLE", "WAREHOUSE_DAILY_REFRESH"):
        monkeypatch.delenv(key, raising=False)
    db.reset_backend()
    db.init(force=True)
    store.upsert(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
          "sector": "Industrials", "active": True}],
        source="test", actor="tester",
    )
    yield
    db.reset_backend()


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Production surface
# --------------------------------------------------------------------------


def test_health_and_workbook_describe_the_whole_warehouse():
    health = production.health()
    assert health["ok"] is True
    assert health["tabs"] == len(TABS)
    assert health["dialect"] in ("sqlite", "postgres")

    workbook = production.workbook()
    assert workbook["tab_count"] == len(TABS)
    assert any(tab["id"] == "annual_sector_ratios" for tab in workbook["tabs"])
    master = next(t for t in workbook["tabs"] if t["id"] == "company_master")
    assert master["rows"] == 1
    assert any(column["key"] == "isin" for column in master["columns"])


def test_sheet_supports_filters_sorting_and_paging():
    store.upsert(
        "daily_market_history",
        [{"symbol": "AAA", "date": f"2026-07-{d:02d}", "close": 100 + d} for d in range(1, 12)],
        source="test", actor="tester",
    )
    page = production.sheet("daily_market_history", sort="date", order="desc", limit=5)
    assert page["total"] == 11
    assert len(page["rows"]) == 5
    assert page["rows"][0]["date"] == "2026-07-11"

    filtered = production.sheet("daily_market_history", filters={"date": "2026-07-05"})
    assert filtered["total"] == 1

    second = production.sheet("daily_market_history", sort="date", order="desc", limit=5, offset=5)
    assert second["rows"][0]["date"] == "2026-07-06"


def test_unknown_tab_is_refused_everywhere():
    assert production.sheet("not_a_tab")["error"].startswith("unknown_tab")
    assert production.edit("not_a_tab", [], actor="a")["error"].startswith("unknown_tab")
    assert production.export("not_a_tab")["error"].startswith("unknown_tab")


# --------------------------------------------------------------------------
# Permissions
# --------------------------------------------------------------------------


def test_roles_gate_writes(monkeypatch):
    monkeypatch.setenv("WAREHOUSE_DEFAULT_ROLE", "read")
    monkeypatch.setenv("WAREHOUSE_EDITORS", "editor@agi.com")
    monkeypatch.setenv("WAREHOUSE_PUBLISHERS", "founder@agi.com")

    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    edit = [{"row_id": row_id, "column": "city", "value": "Mumbai"}]

    assert production.edit("company_master", edit, actor="viewer@agi.com")["error"] == "forbidden"
    assert production.edit("company_master", edit, actor="editor@agi.com", recalc=False)["ok"] is True
    assert production.publish("company_master", actor="editor@agi.com")["error"] == "forbidden"
    assert production.publish("company_master", actor="founder@agi.com")["ok"] is True
    assert production.run_refresh(actor="editor@agi.com", stages=["groww"])["error"] == "forbidden"


def test_writes_require_a_named_actor():
    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    result = production.edit("company_master", [{"row_id": row_id, "column": "city", "value": "X"}],
                             actor="")
    assert result["error"] == "actor_required"


def test_role_description_lists_allowed_actions(monkeypatch):
    monkeypatch.setenv("WAREHOUSE_DEFAULT_ROLE", "approve")
    described = permissions.describe("someone@agi.com")
    assert described["role"] == "approve"
    assert "commit_import" in described["actions"]
    assert "publish" not in described["actions"]


# --------------------------------------------------------------------------
# HTTP routes
# --------------------------------------------------------------------------


def test_http_routes_serve_the_workbook_and_a_sheet():
    from app.api import routes

    health = run(routes.warehouse_health())
    assert health["ok"] is True

    workbook = run(routes.warehouse_workbook())
    assert workbook["tab_count"] == len(TABS)

    sheet = run(routes.warehouse_sheet("company_master", limit=5))
    assert sheet["ok"] is True
    assert sheet["rows"][0]["symbol"] == "AAA"
    assert any(c["computed"] for c in run(routes.warehouse_sheet("historical_ratios"))["columns"])


def test_http_edit_round_trips_and_reports_the_actor():
    from app.api import routes

    row_id = store.fetch("company_master")["rows"][0]["row_id"]
    result = run(
        routes.warehouse_edit(
            "company_master",
            {"edits": [{"row_id": row_id, "column": "city", "value": "Mumbai"}],
             "reason": "profile", "recalculate": False},
            "founder@agi.com",
        )
    )
    assert result["applied"] == 1
    audit = run(routes.warehouse_audit(tab_id="company_master", limit=10))
    assert any(entry["actor"] == "founder@agi.com" for entry in audit["entries"])


def test_http_filters_accept_json():
    from app.api import routes

    store.upsert("daily_market_history",
                 [{"symbol": "AAA", "date": "2026-07-31", "close": 10}],
                 source="test", actor="tester")
    page = run(routes.warehouse_sheet("daily_market_history",
                                      filters=json.dumps({"symbol": {"op": "eq", "value": "AAA"}})))
    assert page["total"] == 1


def test_http_recalculate_delegates_blocking_work(monkeypatch):
    from app.api import routes
    from institutional_warehouse import production as warehouse_production

    seen = {}

    def fake_recompute(**kwargs):
        seen.update(kwargs)
        return {"ok": True, "delegated": True}

    async def fake_threadpool(function, **kwargs):
        seen["function"] = function
        return function(**kwargs)

    monkeypatch.setattr(warehouse_production, "recompute", fake_recompute)
    monkeypatch.setattr(routes, "run_in_threadpool", fake_threadpool)
    result = run(
        routes.warehouse_recalculate(
            {"actor": "scheduler", "stages": ["factors"], "entity": "aaa"},
            None,
        )
    )
    assert result == {"ok": True, "delegated": True}
    assert seen["function"] is fake_recompute
    assert seen["actor"] == "scheduler"
    assert seen["stages"] == ["factors"]
    assert seen["entity"] == "AAA"


# --------------------------------------------------------------------------
# Refresh pipeline
# --------------------------------------------------------------------------


def test_refresh_pipeline_runs_every_stage_and_records_the_run():
    result = refresh.run(actor="tester", limit=5, days=1)
    assert set(result["stages"]) == set(refresh.PIPELINE)
    assert "row_counts" in result
    runs = refresh.recent_runs(5)
    assert runs["runs"][0]["id"] == result["run_id"]


def test_a_failing_stage_does_not_stop_the_pipeline(monkeypatch):
    def explode(**_kwargs):
        raise RuntimeError("collector down")

    monkeypatch.setattr(refresh, "stage_yahoo", explode)
    result = refresh.run(actor="tester", stages=["yahoo", "recalculate"], days=1)
    assert result["ok"] is False
    assert result["stages"]["yahoo"]["error"].startswith("collector down")
    assert result["stages"]["recalculate"]["ok"] is True


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------


def test_scheduler_is_off_unless_enabled():
    assert scheduler.start()["enabled"] is False
    assert scheduler.status()["enabled"] is False


def test_scheduler_slot_defaults_to_the_indian_close(monkeypatch):
    assert scheduler.refresh_slot() == (18, 45)
    monkeypatch.setenv("WAREHOUSE_REFRESH_AT", "20:15")
    assert scheduler.refresh_slot() == (20, 15)
    monkeypatch.setenv("WAREHOUSE_REFRESH_AT", "nonsense")
    assert scheduler.refresh_slot() == (18, 45)


def test_scheduler_runs_once_per_day():
    from datetime import datetime, timedelta, timezone

    today = datetime.now(scheduler.IST)
    before = today.replace(hour=9, minute=0)
    after = today.replace(hour=19, minute=0)
    scheduler._STATE["last_run_date"] = None
    assert scheduler.due(before.astimezone(timezone.utc)) is False
    assert scheduler.due(after.astimezone(timezone.utc)) is True
    scheduler._STATE["last_run_date"] = today.date().isoformat()
    assert scheduler.due(after.astimezone(timezone.utc)) is False
    scheduler._STATE["last_run_date"] = (today - timedelta(days=1)).date().isoformat()
    assert scheduler.due(after.astimezone(timezone.utc)) is True
    scheduler._STATE["last_run_date"] = None
