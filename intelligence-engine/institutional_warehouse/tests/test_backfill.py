"""Historical backfill: resumability, the archive walker, Yahoo loading and
point-in-time valuation reconstruction."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_backfill_"))

from institutional_warehouse import db, history, store, units  # noqa: E402
from institutional_warehouse.backfill import (  # noqa: E402
    checkpoints,
    coverage,
    engine,
    prices,
    statements,
    valuation_history,
)
from institutional_warehouse.backfill.sources import nse_archive, yahoo_history  # noqa: E402
from institutional_warehouse.backfill.validation import chronology_report, screen_series  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    monkeypatch.setenv("WAREHOUSE_BACKFILL_ALLOW_HERE", "true")
    db.reset_backend()
    db.init(force=True)
    store.upsert(
        "company_master",
        [
            {"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
            {"company_id": "BBB", "symbol": "BBB", "company_name": "Beta Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
            {"company_id": "CCC", "symbol": "CCC", "company_name": "Gamma Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
        ],
        source="test", actor="tester",
    )
    yield
    db.reset_backend()


# --------------------------------------------------------------------------
# Fixtures that stand in for the network
# --------------------------------------------------------------------------

BHAV_HEADER = ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE,"
               " CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER")


def bhav_csv(trade_date: str, symbols=("AAA", "BBB")) -> bytes:
    stamp = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    lines = [BHAV_HEADER]
    for index, symbol in enumerate(symbols):
        base = 100 + index * 10
        lines.append(
            f"{symbol}, EQ, {stamp}, {base - 1}, {base}, {base + 5}, {base - 5}, {base + 1},"
            f" {base + 2}, {base + 1}, 100000, 12.5, 500, 50000, 50.0"
        )
    return "\n".join(lines).encode("utf-8")


def archive_fetcher(available: set[str]):
    """Serves only the dates the archive is pretending to have."""
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        name = url.rsplit("/", 1)[-1]
        if "sec_bhavdata_full_" not in name:
            raise RuntimeError("404 not found")
        stamp = name.replace("sec_bhavdata_full_", "").replace(".csv", "")
        iso = f"{stamp[4:8]}-{stamp[2:4]}-{stamp[0:2]}"
        if iso not in available:
            raise RuntimeError("404 not found")
        return bhav_csv(iso)

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def chart_fetcher(symbol_prices: dict[str, list[tuple[str, float]]], *, dividends=None, splits=None):
    def fetch(url: str) -> bytes:
        ticker = url.split("/chart/")[1].split("?")[0].replace(".NS", "").replace(".BO", "")
        rows = symbol_prices.get(ticker)
        if not rows:
            raise RuntimeError("404")
        stamps, opens, highs, lows, closes, volumes, adj = [], [], [], [], [], [], []
        for iso, close in rows:
            moment = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
            stamps.append(int(moment.timestamp()))
            opens.append(close * 0.99)
            highs.append(close * 1.02)
            lows.append(close * 0.98)
            closes.append(close)
            adj.append(close)
            volumes.append(100000)
        events = {}
        if dividends:
            events["dividends"] = {
                str(i): {"date": int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()),
                         "amount": a}
                for i, (d, a) in enumerate(dividends)
            }
        if splits:
            events["splits"] = {
                str(i): {"date": int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()),
                         "splitRatio": r, "numerator": 2, "denominator": 1}
                for i, (d, r) in enumerate(splits)
            }
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": f"{ticker}.NS", "currency": "INR"},
                        "timestamp": stamps,
                        "events": events,
                        "indicators": {
                            "quote": [{"open": opens, "high": highs, "low": lows,
                                       "close": closes, "volume": volumes}],
                            "adjclose": [{"adjclose": adj}],
                        },
                    }
                ],
                "error": None,
            }
        }
        return json.dumps(payload).encode("utf-8")

    return fetch


def month_ends(start_year: int, years: int, price_start: float = 100.0):
    rows = []
    price = price_start
    for year in range(start_year, start_year + years):
        for month in (3, 6, 9, 12):
            rows.append((date(year, month, 28).isoformat(), round(price, 2)))
            price *= 1.03
    return rows


# --------------------------------------------------------------------------
# Archive walker
# --------------------------------------------------------------------------


def test_walker_goes_backwards_instead_of_refetching_today():
    days = [(date(2026, 7, 31) - timedelta(days=n)).isoformat() for n in range(0, 12)]
    available = {d for d in days if datetime.fromisoformat(d).weekday() < 5}
    fetch = archive_fetcher(available)

    result = nse_archive.backfill(actor="tester", days=5, start="2026-07-31", fetch=fetch)
    assert result["days_imported"] == 5
    imported = sorted({r["date"] for r in store.fetch("daily_market_history", limit=500)["rows"]})
    assert len(imported) == 5
    assert imported[-1] == "2026-07-31"
    assert imported[0] < imported[-1]  # it walked back, it did not sit on today


def test_a_completed_date_is_never_downloaded_twice():
    """The bug this phase exists to fix: 406 downloads that produced 3 trading days."""
    available = {"2026-07-31", "2026-07-30", "2026-07-29"}
    first = archive_fetcher(available)
    nse_archive.backfill(actor="tester", days=3, start="2026-07-31", fetch=first)
    assert first.calls

    second = archive_fetcher(available)
    nse_archive.backfill(actor="tester", days=3, start="2026-07-31", fetch=second)

    def requested_dates(calls):
        stamps = set()
        for url in calls:
            name = url.rsplit("/", 1)[-1]
            if "sec_bhavdata_full_" in name:
                raw = name.replace("sec_bhavdata_full_", "").replace(".csv", "")
                stamps.add(f"{raw[4:8]}-{raw[2:4]}-{raw[0:2]}")
        return stamps

    # The second pass moves on to older days and never asks for a completed one.
    assert requested_dates(second.calls).isdisjoint(available)
    assert requested_dates(first.calls) >= available


def test_a_missing_day_is_retired_after_repeated_failures():
    fetch = archive_fetcher(set())  # archive has nothing: every day 404s
    for _ in range(checkpoints.MAX_ATTEMPTS):
        nse_archive.backfill(actor="tester", days=1, start="2026-07-31", fetch=fetch)
    state = checkpoints.date_status(nse_archive.SOURCE, "2026-07-31")
    assert state["status"] == checkpoints.FAILED
    assert state["attempts"] >= checkpoints.MAX_ATTEMPTS
    assert checkpoints.claim_dates(nse_archive.SOURCE, ["2026-07-31"]) == []


def test_backfill_resumes_where_it_stopped():
    available = {(date(2026, 7, 31) - timedelta(days=n)).isoformat() for n in range(0, 20)}
    fetch = archive_fetcher(available)
    first = nse_archive.backfill(actor="tester", days=3, start="2026-07-31", fetch=fetch)
    second = nse_archive.backfill(actor="tester", days=3, start="2026-07-31", fetch=fetch)
    assert first["days_imported"] == 3
    assert second["days_imported"] == 3
    assert set(second["coverage"]["by_status"]) == {checkpoints.DONE}
    assert second["coverage"]["days_done"] == 6
    assert second["last"] < first["first"]  # the second slice is strictly older


# --------------------------------------------------------------------------
# Yahoo prices
# --------------------------------------------------------------------------


def test_yahoo_history_loads_decades_of_prices_dividends_and_splits():
    rows = month_ends(2006, 20)
    fetch = chart_fetcher({"AAA": rows},
                          dividends=[("2024-06-28", 5.0)],
                          splits=[("2015-06-28", "2:1")])
    result = prices.backfill_company("AAA", actor="tester", fetch=fetch)

    assert result["ok"] is True
    assert result["rows"] == len(rows)
    assert result["years"] > 19
    stored = store.fetch("daily_market_history", entity="AAA", limit=200)
    assert stored["total"] == len(rows)
    actions = {r["action_type"] for r in store.fetch("corporate_actions", entity="AAA")["rows"]}
    assert actions == {"dividend", "split"}


def test_price_backfill_is_checkpointed_and_skips_completed_companies():
    fetch = chart_fetcher({"AAA": month_ends(2020, 3), "BBB": month_ends(2020, 3)})
    first = prices.backfill(["AAA", "BBB"], actor="tester", limit=10, fetch=fetch)
    assert first["companies_done"] == 2

    second = prices.backfill(["AAA", "BBB"], actor="tester", limit=10, fetch=fetch)
    assert second["queued"] == 0
    assert second["companies_done"] == 0

    refreshed = prices.backfill(["AAA"], actor="tester", limit=10, fetch=fetch, refresh_done=True)
    assert refreshed["queued"] == 1


def test_a_failing_company_records_the_error_and_does_not_stop_the_run():
    fetch = chart_fetcher({"AAA": month_ends(2020, 2)})  # BBB is absent
    result = prices.backfill(["AAA", "BBB"], actor="tester", limit=10, fetch=fetch)
    assert result["companies_done"] == 1
    assert result["companies_failed"] == 1
    assert checkpoints.checkpoint(prices.KIND, "BBB")["status"] == checkpoints.FAILED


# --------------------------------------------------------------------------
# Series screening
# --------------------------------------------------------------------------


def test_screening_rejects_impossible_rows_and_warns_on_price_breaks():
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat()
    report = screen_series(
        [
            {"symbol": "AAA", "date": "2026-01-01", "close": 100, "high": 101, "low": 99},
            {"symbol": "AAA", "date": "2026-01-02", "close": -5},
            {"symbol": "AAA", "date": "2026-01-03", "close": 100, "high": 90, "low": 95},
            {"symbol": "AAA", "date": "2026-01-01", "close": 100},
            {"symbol": "AAA", "date": tomorrow, "close": 100},
            {"symbol": "AAA", "date": "2026-01-06", "close": 45},
        ]
    )
    codes = {i["code"] for entry in report["rejected"] for i in entry["issues"]}
    assert "impossible_price" in codes
    assert "impossible_range" in codes
    assert "duplicate_date" in codes
    assert "future_date" in codes
    warn_codes = {i["code"] for entry in report["warnings"] for i in entry["issues"]}
    assert "unexplained_price_break" in warn_codes
    assert report["accepted_count"] == 2


def test_chronology_report_finds_the_holes():
    rows = [{"date": "2026-01-01"}, {"date": "2026-01-02"}, {"date": "2026-03-01"}]
    report = chronology_report(rows)
    assert report["points"] == 3
    assert report["gap_count"] == 1
    assert report["gaps"][0]["days"] == 58


# --------------------------------------------------------------------------
# Statements
# --------------------------------------------------------------------------


def test_statement_backfill_stores_raw_periods_only():
    def loader(symbol):
        return {
            "ok": True,
            "symbol": symbol,
            "annual": [
                {"fiscal_label": "FY24", "period_end": "2024-03-31", "revenue": 1000.0,
                 "pat": 100.0, "equity": 500.0, "shares_outstanding": 100.0},
                {"fiscal_label": "FY25", "period_end": "2025-03-31", "revenue": 1200.0,
                 "pat": 140.0, "equity": 600.0, "shares_outstanding": 100.0},
            ],
            "quarterly": [
                {"fiscal_label": "FY25Q1", "period_end": "2024-06-30", "revenue": 280.0, "pat": 30.0},
            ],
        }

    result = statements.backfill_company("AAA", actor="tester", loader=loader)
    assert result["annual_periods"] == 2
    assert result["quarterly_periods"] == 1
    row = store.fetch("financials_annual", entity="AAA", filters={"fiscal_year": "FY25"})["rows"][0]
    # Yahoo reports absolute rupees; the warehouse stores INR million.
    assert row["revenue"] == pytest.approx(1200.0 / units.MILLION)
    assert row["_meta"]["reported_unit"] == "rupee"
    assert row["free_cash_flow"] is None  # derived values are not the backfill's job


def test_indian_fiscal_labels():
    assert yahoo_history.fiscal_label("2025-03-31", quarterly=False) == "FY25"
    assert yahoo_history.fiscal_label("2025-06-30", quarterly=False) == "FY26"
    assert yahoo_history.fiscal_label("2025-06-30", quarterly=True) == "FY26Q1"
    assert yahoo_history.fiscal_label("2024-12-31", quarterly=True) == "FY25Q3"


# --------------------------------------------------------------------------
# Point-in-time valuation
# --------------------------------------------------------------------------


def _seed_for_reconstruction(symbol="AAA"):
    prices_fetch = chart_fetcher({symbol: month_ends(2015, 11)})
    prices.backfill_company(symbol, actor="tester", fetch=prices_fetch)

    def loader(_symbol):
        return {
            "ok": True,
            "symbol": symbol,
            "annual": [
                {"fiscal_label": f"FY{str(year)[-2:]}", "period_end": f"{year}-03-31",
                 "revenue": 1000.0 * (year - 2014), "pat": 100.0 * (year - 2014),
                 "equity": 500.0 * (year - 2014), "shares_outstanding": 100.0,
                 "debt": 250.0, "cash": 50.0, "ebitda": 200.0 * (year - 2014)}
                for year in range(2016, 2026)
            ],
            "quarterly": [],
        }

    statements.backfill_company(symbol, actor="tester", loader=loader)


def test_reconstruction_writes_point_in_time_observations():
    _seed_for_reconstruction()
    result = valuation_history.reconstruct_company("AAA", actor="tester", cadence="quarterly")
    assert result["ok"] is True
    assert result["observations"] > 20
    assert result.get("reconstruction_version") == "8.3B"
    assert result.get("vendor_historical_ratios") is False

    rows = store.fetch("historical_valuation", entity="AAA", sort="date", order="asc",
                       limit=500)["rows"]
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)
    assert len({r["date"] for r in rows}) == len(rows)   # one observation per date
    assert any(r["pe"] for r in rows)
    assert any(r["pb"] for r in rows)
    assert any(r.get("enterprise_value") for r in rows)
    assert any(r.get("roe") for r in rows)


def test_reconstruction_prefers_consolidated_statements():
    """Phase 8.3B — never mix CONSOLIDATED and STANDALONE in one series."""
    from institutional_warehouse import gateway

    prices_fetch = chart_fetcher({"AAA": month_ends(2022, 4)})
    prices.backfill_company("AAA", actor="tester", fetch=prices_fetch)
    gateway.write(
        "financials_annual",
        [
            {
                "symbol": "AAA",
                "statement_type": "STANDALONE",
                "fiscal_year": "FY24",
                "revenue": 500.0,
                "pat": 50.0,
                "equity": 200.0,
                "shares_outstanding": 100.0,
                "debt": 10.0,
                "cash": 5.0,
                "ebitda": 80.0,
                "source": "test",
            },
            {
                "symbol": "AAA",
                "statement_type": "CONSOLIDATED",
                "fiscal_year": "FY24",
                "revenue": 1000.0,
                "pat": 100.0,
                "equity": 500.0,
                "shares_outstanding": 100.0,
                "debt": 250.0,
                "cash": 50.0,
                "ebitda": 200.0,
                "source": "test",
            },
            {
                "symbol": "AAA",
                "statement_type": "CONSOLIDATED",
                "fiscal_year": "FY25",
                "revenue": 1200.0,
                "pat": 140.0,
                "equity": 600.0,
                "shares_outstanding": 100.0,
                "debt": 250.0,
                "cash": 50.0,
                "ebitda": 240.0,
                "source": "test",
            },
        ],
        source="test",
        actor="tester",
        reason="test_consolidated_preference",
    )
    out = valuation_history.reconstruct_company("AAA", actor="tester", cadence="quarterly")
    assert out["ok"] is True
    assert out["statement_type"] == "CONSOLIDATED"
    timeline = valuation_history._statement_timeline("AAA")
    assert all(e["statement_type"] == "CONSOLIDATED" for e in timeline)


def test_reconstruction_never_uses_a_statement_before_it_was_published():
    """The FY25 result (period end 31 Mar 2025) cannot inform a March 2025 valuation."""
    _seed_for_reconstruction()
    valuation_history.reconstruct_company("AAA", actor="tester", cadence="quarterly")

    timeline = valuation_history._statement_timeline("AAA")
    fy25 = next(e for e in timeline if e["label"] == "FY25")
    assert fy25["known_at"] > "2025-03-31"

    march = [r for r in store.fetch("historical_valuation", entity="AAA", limit=500)["rows"]
             if r["date"].startswith("2025-03")]
    if march:
        used = valuation_history._latest_known(timeline, march[0]["date"], quarterly=False)
        assert used is not None
        assert used["label"] != "FY25"    # only FY24 and earlier were public then


def test_availability_dates_respect_the_reporting_lag():
    assert valuation_history.available_from("FY25", quarterly=False) == "2025-05-30"
    assert valuation_history.available_from("FY2025", quarterly=False) == "2025-05-30"
    assert valuation_history.available_from("2025", quarterly=False) == "2025-05-30"
    assert valuation_history.available_from("FY25Q2", quarterly=True) == "2024-11-14"
    assert valuation_history.available_from("FY2025Q2", quarterly=True) == "2024-11-14"
    assert valuation_history.available_from("FY25", quarterly=False, lag_days=0) == "2025-03-31"


def test_cross_sectional_rerank_places_a_company_against_its_peers():
    for symbol, price_start in (("AAA", 100.0), ("BBB", 400.0), ("CCC", 40.0)):
        fetch = chart_fetcher({symbol: month_ends(2022, 3, price_start=price_start)})
        prices.backfill_company(symbol, actor="tester", fetch=fetch)

        def loader(_s, sym=symbol):
            return {
                "ok": True, "symbol": sym,
                "annual": [
                    {"fiscal_label": f"FY{str(y)[-2:]}", "period_end": f"{y}-03-31",
                     "revenue": 1000.0, "pat": 100.0, "equity": 500.0,
                     "shares_outstanding": 100.0, "ebitda": 200.0}
                    for y in range(2022, 2026)
                ],
                "quarterly": [],
            }

        statements.backfill_company(symbol, actor="tester", loader=loader)
        valuation_history.reconstruct_company(symbol, actor="tester", cadence="quarterly")

    dates = sorted({r["date"] for r in store.fetch("historical_valuation", limit=2000)["rows"]})
    ranked = valuation_history.rerank_dates(dates, actor="tester")
    assert ranked["rows_updated"] > 0

    latest = dates[-1]
    rows = {r["symbol"]: r for r in
            store.fetch("historical_valuation", filters={"date": latest}, limit=50)["rows"]}
    assert rows["AAA"]["sector_median"] is not None
    # BBB is priced highest on identical earnings, so it must be the most expensive.
    assert rows["BBB"]["pe"] > rows["AAA"]["pe"] > rows["CCC"]["pe"]
    assert rows["CCC"]["percentile"] > rows["BBB"]["percentile"]


# --------------------------------------------------------------------------
# Engine, coverage and history reads
# --------------------------------------------------------------------------


def test_engine_refuses_to_run_outside_the_worker(monkeypatch):
    monkeypatch.delenv("WAREHOUSE_BACKFILL_ALLOW_HERE", raising=False)
    monkeypatch.setenv("AGI_ROLE", "web")
    result = engine.run(actor="tester")
    assert result["ok"] is False
    assert result["error"] == "worker_only"

    monkeypatch.setenv("AGI_ROLE", "gather_worker")
    assert engine.worker_only() is None


def test_engine_runs_every_stage_and_records_a_job():
    fetch = chart_fetcher({"AAA": month_ends(2020, 5), "BBB": month_ends(2020, 5)})
    result = engine.run(
        actor="tester",
        universe=["AAA", "BBB"],
        companies=5,
        days=2,
        fetch=fetch,
        statement_loader=lambda s: {"ok": True, "symbol": s, "annual": [
            {"fiscal_label": "FY24", "period_end": "2024-03-31", "revenue": 900.0,
             "pat": 90.0, "equity": 450.0, "shares_outstanding": 100.0}], "quarterly": []},
        enforce_worker=False,
    )
    assert set(result["stages"]) == set(engine.STAGES)
    jobs = checkpoints.recent_jobs(limit=1)
    assert jobs[0]["id"] == result["job_id"]
    assert jobs[0]["status"] in (checkpoints.DONE, checkpoints.FAILED)


def test_coverage_dashboard_reports_depth_by_company_and_sector():
    fetch = chart_fetcher({"AAA": month_ends(2004, 22), "BBB": month_ends(2022, 2)})
    prices.backfill(["AAA", "BBB"], actor="tester", limit=5, fetch=fetch)

    board = coverage.dashboard()
    assert board["summary"]["companies_with_history"] == 2
    assert board["summary"]["max_years"] > 20
    assert board["summary"]["tiers"]["20y+"] >= 1
    sectors = {s["sector"] for s in board["sectors"]}
    assert "Industrials" in sectors
    tables = {t["table"]: t for t in board["tables"]}
    assert tables["daily_market_history"]["rows"] > 0


def test_history_series_computes_cagr_at_query_time():
    fetch = chart_fetcher({"AAA": [("2016-03-31", 100.0), ("2021-03-31", 200.0),
                                   ("2026-03-31", 400.0)]})
    prices.backfill_company("AAA", actor="tester", fetch=fetch)

    result = history.series("AAA", "price", window="max")
    assert result["ok"] is True
    assert result["count"] == 3
    assert result["stats"]["first"] == 100.0
    assert result["stats"]["last"] == 400.0
    assert result["stats"]["cagr_pct"] == pytest.approx(14.87, abs=0.1)
    assert result["stats"]["years"] == pytest.approx(10.0, abs=0.05)


def test_history_window_filters_the_series():
    recent = (datetime.now(timezone.utc).date() - timedelta(days=200)).isoformat()
    old = (datetime.now(timezone.utc).date() - timedelta(days=2000)).isoformat()
    fetch = chart_fetcher({"AAA": [(old, 50.0), (recent, 150.0)]})
    prices.backfill_company("AAA", actor="tester", fetch=fetch)

    assert history.series("AAA", "price", window="1y")["count"] == 1
    assert history.series("AAA", "price", window="max")["count"] == 2


def test_as_at_returns_what_was_known_on_a_date():
    fetch = chart_fetcher({"AAA": [("2020-03-31", 80.0), ("2024-03-28", 250.0)]})
    prices.backfill_company("AAA", actor="tester", fetch=fetch)
    snapshot = history.as_at("AAA", "2021-01-01")
    assert snapshot["ok"] is True
    assert snapshot["price"]["date"] == "2020-03-31"   # not the 2024 print


def test_history_compare_ranks_companies_on_one_metric():
    fetch = chart_fetcher({
        "AAA": [("2021-03-31", 100.0), ("2026-03-31", 400.0)],
        "BBB": [("2021-03-31", 100.0), ("2026-03-31", 120.0)],
    })
    prices.backfill(["AAA", "BBB"], actor="tester", limit=5, fetch=fetch)
    result = history.compare(["AAA", "BBB"], "price", window="max")
    assert result["ranking"][0]["symbol"] == "AAA"
    assert result["ranking"][0]["cagr_pct"] > result["ranking"][1]["cagr_pct"]


def test_history_coverage_per_company():
    fetch = chart_fetcher({"AAA": month_ends(2010, 15)})
    prices.backfill_company("AAA", actor="tester", fetch=fetch)
    report = history.coverage("AAA")
    assert report["price_years"] > 14
    assert report["tabs"]["daily_market_history"]["rows"] == 60


class TestEquitySeries:
    """Which rows in a bhavcopy are a company's shares.

    This collector exists to fix survivorship bias. It kept EQ and BE, which
    excluded the failures it was built to capture - a company on its way out is
    moved to BZ, the surveillance series, before it is delisted.
    """

    @staticmethod
    def _row(symbol: str, series: str, close: str = "101.0") -> str:
        return (f"{symbol}, {series}, 15-Jun-2020, 100.0, 100.0, 105.0, 95.0, 100.5,"
                f" {close}, 100.5, 100000, 12.5, 500, 50000, 50.0")

    def _parse(self, *rows: str):
        text = "\n".join([BHAV_HEADER, *rows])
        return nse_archive.parse_rows(text, "2020-06-15")

    def test_a_company_on_its_way_out_is_collected(self):
        """Cox & Kings sat in BZ at 1.25 rupees on 15 June 2020 and was dropped
        on every pass, which is exactly the loss a backtest must be able to
        take."""
        rows = self._parse(self._row("COX&KINGS", "BZ", "1.25"))
        assert [r["symbol"] for r in rows] == ["COX&KINGS"]
        assert rows[0]["close"] == 1.25

    def test_the_sme_board_is_collected(self):
        """Those companies delist too; leaving them out repeats the bias one
        tier down."""
        assert len(self._parse(self._row("SMECO", "SM"), self._row("SMETT", "ST"))) == 2

    def test_ordinary_and_trade_for_trade_equity_still_load(self):
        assert len(self._parse(self._row("AAA", "EQ"), self._row("BBB", "BE"))) == 2

    @pytest.mark.parametrize("series", ["GB", "GS", "N2", "NZ", "Y1", "Z9", "RR", "MF"])
    def test_debt_and_other_instruments_are_not_companies(self, series):
        assert self._parse(self._row("SOMEBOND", series)) == []

    def test_a_block_deal_never_becomes_a_second_close(self):
        """BL is the block-deal window - a second price for a symbol on a day it
        already has one. Admitting it would overwrite the real close."""
        rows = self._parse(self._row("AAA", "EQ", "101.0"), self._row("AAA", "BL", "97.0"))
        assert [r["close"] for r in rows] == [101.0]

    def test_the_filter_is_an_allow_list(self):
        """Around ninety series codes appear across the archive and NSE adds
        more. A deny-list would let each new one in silently."""
        assert self._parse(self._row("NEWTHING", "Q7")) == []


class TestReopenDates:
    """Sending already-collected days back through the collector.

    A day is claimed once and never again, which is right when the collector is
    right and wrong after a fix that changes what a day contains.
    """

    def test_a_done_day_is_claimed_again_after_reopening(self):
        checkpoints.mark_date("src_reopen", "2020-06-15", status="done", rows=1622)
        assert checkpoints.claim_dates("src_reopen", ["2020-06-15"]) == []
        checkpoints.reopen_dates("src_reopen", reason="series filter widened to BZ and SME")
        assert checkpoints.claim_dates("src_reopen", ["2020-06-15"]) == ["2020-06-15"]

    def test_a_day_that_had_failed_starts_over_rather_than_resuming(self):
        """A day two-thirds of the way to being abandoned is not still two-thirds
        of the way there once the reason it failed has changed underneath it."""
        for _ in range(3):
            checkpoints.mark_date("src_att", "2020-06-16", status="failed", error="boom")
        assert checkpoints.claim_dates("src_att", ["2020-06-16"]) == [], "exhausted"
        checkpoints.reopen_dates("src_att", reason="parser fixed")
        assert checkpoints.claim_dates("src_att", ["2020-06-16"]) == ["2020-06-16"]
        assert checkpoints.date_status("src_att", "2020-06-16")["attempts"] == 0

    def test_it_can_be_limited_to_a_range(self):
        for day in ("2019-01-02", "2021-01-04", "2023-01-03"):
            checkpoints.mark_date("src_range", day, status="done", rows=10)
        out = checkpoints.reopen_dates("src_range", reason="only the old ones",
                                       before="2022-01-01")
        assert out["reopened"] == 2
        assert checkpoints.claim_dates("src_range", ["2023-01-03"]) == [], "left alone"

    def test_it_reports_what_it_touched(self):
        for day in ("2020-02-03", "2020-02-04"):
            checkpoints.mark_date("src_report", day, status="done", rows=5)
        out = checkpoints.reopen_dates("src_report", reason="widened filter")
        assert (out["reopened"], out["oldest"], out["newest"]) == (2, "2020-02-03", "2020-02-04")

    def test_a_reopen_without_a_reason_is_refused(self):
        """A day silently sent round again is indistinguishable from a collector
        looping on itself."""
        checkpoints.mark_date("src_noreason", "2020-06-15", status="done", rows=1)
        assert checkpoints.reopen_dates("src_noreason", reason=" ")["error"] == "reason_required"
        assert checkpoints.claim_dates("src_noreason", ["2020-06-15"]) == []

    def test_reopening_leaves_the_collected_prices_in_place(self):
        """The re-run writes through the same upsert. Deleting first would leave
        a hole for as long as the re-run takes, and permanently if it stalls."""
        nse_archive.backfill(actor="tester", days=1, start="2026-07-31",
                             fetch=archive_fetcher({"2026-07-31"}))
        before = store.all_rows("daily_market_history", limit=5000)
        assert before, "the collector should have stored something to protect"
        checkpoints.reopen_dates(nse_archive.SOURCE, reason="series filter widened")
        after = store.all_rows("daily_market_history", limit=5000)
        assert len(after) == len(before)


class TestWalkFollowsTheFrontier:
    """How far back a scheduled slice can ever see.

    The walker counts a fixed number of weekdays backwards. Counted from today
    that caps the reach at roughly the window's own length - about eleven months
    at the scheduled size - while the archive goes back to 1995. It reached 2022
    only because an explicit start was passed by hand.
    """

    def test_with_nothing_collected_it_starts_at_the_top(self):
        claimed = nse_archive.backfill(actor="tester", days=2,
                                       fetch=archive_fetcher(set()))
        assert claimed["ok"] is not False

    def test_the_window_moves_back_as_days_are_collected(self):
        source = nse_archive.SOURCE
        checkpoints.mark_date(source, "2023-03-20", status="done", rows=10)
        assert checkpoints.frontier_date(source) == "2023-03-20"
        checkpoints.mark_date(source, "2023-03-17", status="done", rows=10)
        assert checkpoints.frontier_date(source) == "2023-03-17", "frontier follows the oldest"

    def test_a_day_that_failed_does_not_move_the_frontier(self):
        """Otherwise one unreachable day would drag the window past everything
        behind it, and those days would never be looked at again."""
        source = "src_frontier_fail"
        checkpoints.mark_date(source, "2023-03-20", status="done", rows=10)
        checkpoints.mark_date(source, "2019-01-02", status="failed", error="404")
        assert checkpoints.frontier_date(source) == "2023-03-20"

    def test_a_source_that_has_collected_nothing_has_no_frontier(self):
        assert checkpoints.frontier_date("src_never_run") is None

    def test_both_the_newest_and_the_oldest_end_are_offered(self):
        """One window cannot do both jobs: counted from today the walk never
        digs, counted from the frontier it never notices this morning's file."""
        source = nse_archive.SOURCE
        checkpoints.mark_date(source, "2023-03-20", status="done", rows=10)
        seen = []

        def watching(url: str) -> bytes:
            seen.append(url)
            raise FileNotFoundError(url)

        nse_archive.backfill(actor="tester", days=3, fetch=watching)
        years = {u.split("sec_bhavdata_full_")[-1][4:8] for u in seen if "sec_bhavdata_full_" in u}
        assert "2023" in years, "must look near the frontier"
        assert len(years) > 1, "must also look near today"

    def test_a_backlog_at_the_top_does_not_starve_the_dig(self):
        """Reopening 943 recent days filled the top window completely. Offered
        as one combined list, the recent end takes the whole slice and the deep
        end never gets a turn - which is the stall, not a fix for it."""
        source = nse_archive.SOURCE
        checkpoints.mark_date(source, "2023-03-20", status="done", rows=10)
        seen = []

        def watching(url: str) -> bytes:
            seen.append(url)
            raise FileNotFoundError(url)

        nse_archive.backfill(actor="tester", days=8, fetch=watching)
        years = {u.split("sec_bhavdata_full_")[-1][4:8] for u in seen if "sec_bhavdata_full_" in u}
        assert "2023" in years, "the dig must get a share of every slice"

    def test_the_dig_gets_most_of_the_slice(self):
        """Keeping up with new days needs a few slots. Reaching 2016 needs the
        rest, and there are roughly 2,600 weekdays to cross."""
        assert nse_archive.RECENT_SHARE <= 0.5
