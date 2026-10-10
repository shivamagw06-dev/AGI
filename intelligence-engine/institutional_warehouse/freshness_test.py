"""The monitor's own failure mode is reporting healthy, so assert it cannot."""
from __future__ import annotations

import sys
import types
from datetime import date

from institutional_warehouse import freshness


def _install_fake_db(monkey, *, counts, newest):
    """A db module standing in for the warehouse."""
    fake = types.SimpleNamespace(
        physical_table=lambda tab: tab,
        count=lambda table: counts.get(table, 0),
        query=lambda sql: [{"newest": _answer(sql, newest)}],
    )
    monkey.setitem(sys.modules, "institutional_warehouse.db", fake)


def _answer(sql, newest):
    for tab, value in newest.items():
        if f"FROM {tab}" in sql:
            return value
    return None


def test_audit_column_prefers_last_updated():
    # 76 of 85 tables carry it; the fallbacks exist for the nine that do not.
    assert freshness._audit_column("financials_annual") == "last_updated"
    assert freshness._audit_column("strategy_definitions") == "created_at"
    assert freshness._audit_column("strategy_live_attribution") == "as_of"


def test_audit_column_never_returns_a_business_date():
    # max(listing_date) is the newest listing, not proof the table is alive.
    # Reading one as the other is how a monitor comes to report a dead feed ok.
    assert freshness._audit_column("company_master") == "last_updated"
    assert freshness._audit_column("daily_market_history") != "date"


def test_every_table_but_two_can_be_watched():
    # 83 of 85 carry a column saying when a row was written. The two that do not
    # are named here so that adding one is a visible change rather than a quiet
    # drop in coverage.
    from institutional_warehouse import schema
    blind = {t for t in schema.tab_ids() if freshness._audit_column(t) is None}
    assert blind == {"point_in_time_observations", "universe_membership_history"}


def test_a_table_that_stopped_being_written_is_silent(monkeypatch):
    _install_fake_db(monkeypatch, counts={"macro_series": 4000},
                     newest={"macro_series": "2026-01-01"})
    row = freshness._derived_row("macro_series", date(2026, 8, 25))
    assert row["status"] == freshness.SILENT
    assert row["age_days"] > freshness.SILENT_AFTER_DAYS


def test_a_table_still_being_written_is_ok(monkeypatch):
    _install_fake_db(monkeypatch, counts={"macro_series": 4000},
                     newest={"macro_series": "2026-08-24"})
    assert freshness._derived_row("macro_series", date(2026, 8, 25))["status"] == freshness.OK


def test_an_empty_table_is_reported_but_not_called_broken(monkeypatch):
    # 25 tables were empty the day this was written -- built, never filled.
    # Calling that a failure every day would train everyone to ignore the report.
    _install_fake_db(monkeypatch, counts={}, newest={})
    row = freshness._derived_row("portfolio_holdings", date(2026, 8, 25))
    assert row["status"] == freshness.EMPTY
    assert row["status"] != freshness.SILENT


def test_a_table_with_no_write_column_says_so(monkeypatch):
    _install_fake_db(monkeypatch, counts={"universe_membership_history": 10},
                     newest={})
    row = freshness._derived_row("universe_membership_history", date(2026, 8, 25))
    assert row["status"] == freshness.UNWATCHABLE
    assert row["note"]
    # Not silently ok: a table nobody can check must not read as a table that
    # passed a check.
    assert row["status"] != freshness.OK


def test_the_report_covers_every_table_in_the_schema(monkeypatch):
    # The point of the change. Thirteen of eighty-five were watched, so a
    # collector could stop and nothing would say so. A new table must be
    # covered by existing, not by someone remembering to declare it.
    from institutional_warehouse import schema
    _install_fake_db(monkeypatch, counts={t: 10 for t in schema.tab_ids()},
                     newest={t: "2026-08-25" for t in schema.tab_ids()})
    report = freshness.report(today="2026-08-25")

    covered = {t["tab"] for t in report["tables"]}
    assert covered == set(schema.tab_ids())
    assert len(report["tables"]) == len(covered), "a table is reported twice"
    assert report["coverage"]["declared"] == len(freshness.EXPECTED)


def test_derived_rows_cannot_make_the_report_fail(monkeypatch):
    # Seventy-two weak checks must not be able to drown the thirteen sharp ones.
    # A silent table is surfaced in its own list, not folded into `late`.
    from institutional_warehouse import schema
    every = schema.tab_ids()
    _install_fake_db(monkeypatch, counts={t: 10 for t in every},
                     newest={t: "2020-01-01" for t in every if t not in freshness.EXPECTED}
                             | {t: "2026-08-25" for t in freshness.EXPECTED})
    report = freshness.report(today="2026-08-25")

    assert report["ok"] is True, "declared checks all pass, so the report passes"
    assert report["late"] == 0
    assert len(report["silent"]) > 50, "but the dead tables are still named"
