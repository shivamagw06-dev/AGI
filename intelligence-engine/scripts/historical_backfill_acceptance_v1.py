#!/usr/bin/env python3
"""Phase 7.1a acceptance — historical backfill and time-series reads.

Proves the phase's contract without depending on the network: a recorded
archive and a recorded Yahoo chart stand in for the sources, exercising exactly
the code that runs on the worker.

  1. the archive walker goes backwards instead of re-fetching today
  2. a completed trading day is never downloaded twice
  3. an interrupted backfill resumes where it stopped
  4. Yahoo history loads decades of prices with dividends and splits
  5. statements land as raw periods, with no derived metrics
  6. valuation history is reconstructed as point-in-time observations
  7. no observation uses a statement published after that date
  8. the cross-sectional pass ranks each company against same-day peers
  9. series reads compute CAGR and percentile at query time
 10. coverage reports depth by company, sector and table

Run:
    cd intelligence-engine
    INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_hist PYTHONPATH=. \
        python3 scripts/historical_backfill_acceptance_v1.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os  # noqa: E402

os.environ.setdefault("WAREHOUSE_BACKFILL_ALLOW_HERE", "true")

from institutional_warehouse import db, history, store  # noqa: E402
from institutional_warehouse.backfill import (  # noqa: E402
    checkpoints,
    coverage,
    engine,
    prices,
    statements,
    valuation_history,
)
from institutional_warehouse.backfill.sources import nse_archive  # noqa: E402

ACTOR = "acceptance@agi"
RESULTS: list[dict[str, Any]] = []
UNIVERSE = ("AAA", "BBB", "CCC")

BHAV_HEADER = ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE,"
               " CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER")


# --------------------------------------------------------------------------
# Recorded sources
# --------------------------------------------------------------------------


def bhav_csv(trade_date: str) -> bytes:
    stamp = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    lines = [BHAV_HEADER]
    for index, symbol in enumerate(UNIVERSE):
        base = 100 + index * 25
        lines.append(
            f"{symbol}, EQ, {stamp}, {base - 1}, {base}, {base + 4}, {base - 4}, {base + 1},"
            f" {base + 2}, {base + 1}, 250000, 30.5, 900, 120000, 48.0"
        )
    return "\n".join(lines).encode("utf-8")


def archive_fetcher(available: set[str]) -> Callable[[str], bytes]:
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        name = url.rsplit("/", 1)[-1]
        if "sec_bhavdata_full_" not in name:
            raise RuntimeError("404")
        raw = name.replace("sec_bhavdata_full_", "").replace(".csv", "")
        iso = f"{raw[4:8]}-{raw[2:4]}-{raw[0:2]}"
        if iso not in available:
            raise RuntimeError("404")
        return bhav_csv(iso)

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def quarter_ends(start_year: int, years: int, price_start: float) -> list[tuple[str, float]]:
    rows, price = [], price_start
    for year in range(start_year, start_year + years):
        for month in (3, 6, 9, 12):
            rows.append((date(year, month, 28).isoformat(), round(price, 2)))
            price *= 1.028
    return rows


PRICE_BOOK = {
    "AAA": quarter_ends(2004, 22, 60.0),
    "BBB": quarter_ends(2010, 16, 400.0),
    "CCC": quarter_ends(2018, 8, 35.0),
}


def chart_fetcher() -> Callable[[str], bytes]:
    def fetch(url: str) -> bytes:
        ticker = url.split("/chart/")[1].split("?")[0].replace(".NS", "").replace(".BO", "")
        rows = PRICE_BOOK.get(ticker)
        if not rows:
            raise RuntimeError("404")
        stamps, closes = [], []
        for iso, close in rows:
            stamps.append(int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp()))
            closes.append(close)
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": f"{ticker}.NS", "currency": "INR"},
                        "timestamp": stamps,
                        "events": {
                            "dividends": {
                                "1": {
                                    "date": int(datetime.fromisoformat("2024-06-28")
                                                .replace(tzinfo=timezone.utc).timestamp()),
                                    "amount": 4.0,
                                }
                            },
                            "splits": {
                                "1": {
                                    "date": int(datetime.fromisoformat("2016-06-28")
                                                .replace(tzinfo=timezone.utc).timestamp()),
                                    "splitRatio": "2:1", "numerator": 2, "denominator": 1,
                                }
                            },
                        },
                        "indicators": {
                            "quote": [{
                                "open": [c * 0.99 for c in closes],
                                "high": [c * 1.02 for c in closes],
                                "low": [c * 0.98 for c in closes],
                                "close": closes,
                                "volume": [250000] * len(closes),
                            }],
                            "adjclose": [{"adjclose": closes}],
                        },
                    }
                ],
                "error": None,
            }
        }
        return json.dumps(payload).encode("utf-8")

    return fetch


def statement_loader(symbol: str) -> dict[str, Any]:
    return {
        "ok": True,
        "symbol": symbol,
        "annual": [
            {
                "fiscal_label": f"FY{str(year)[-2:]}",
                "period_end": f"{year}-03-31",
                "revenue": 1000.0 * (year - 2013),
                "ebitda": 200.0 * (year - 2013),
                "pat": 100.0 * (year - 2013),
                "equity": 500.0 * (year - 2013),
                "debt": 300.0,
                "cash": 80.0,
                "shares_outstanding": 100.0,
            }
            for year in range(2015, 2026)
        ],
        "quarterly": [],
    }


def check(name: str, fn: Callable[[], tuple[bool, Any]]) -> bool:
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as exc:
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    RESULTS.append({"case": name, "pass": bool(ok), "detail": detail,
                    "ms": int((time.perf_counter() - t0) * 1000)})
    return bool(ok)


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


def case_walks_backwards() -> tuple[bool, Any]:
    available = {(date(2026, 7, 31) - timedelta(days=n)).isoformat() for n in range(0, 30)}
    fetch = archive_fetcher(available)
    result = nse_archive.backfill(actor=ACTOR, days=6, start="2026-07-31", fetch=fetch)
    stored = sorted({r["date"] for r in store.fetch("daily_market_history", limit=500)["rows"]})
    return (
        result["days_imported"] == 6 and len(stored) == 6 and stored[0] < stored[-1],
        {"days": result["days_imported"], "from": stored[0], "to": stored[-1]},
    )


def case_no_repeat_downloads() -> tuple[bool, Any]:
    done = checkpoints.completed_dates(nse_archive.SOURCE)
    fetch = archive_fetcher({(date(2026, 7, 31) - timedelta(days=n)).isoformat() for n in range(0, 30)})
    nse_archive.backfill(actor=ACTOR, days=4, start="2026-07-31", fetch=fetch)
    asked = set()
    for url in fetch.calls:
        raw = url.rsplit("/", 1)[-1].replace("sec_bhavdata_full_", "").replace(".csv", "")
        if len(raw) == 8:
            asked.add(f"{raw[4:8]}-{raw[2:4]}-{raw[0:2]}")
    return (
        asked.isdisjoint(done) and bool(asked),
        {"previously_done": len(done), "newly_requested": len(asked), "overlap": len(asked & done)},
    )


def case_resumes() -> tuple[bool, Any]:
    before = checkpoints.date_coverage(nse_archive.SOURCE)["days_done"]
    fetch = archive_fetcher({(date(2026, 7, 31) - timedelta(days=n)).isoformat() for n in range(0, 60)})
    nse_archive.backfill(actor=ACTOR, days=5, start="2026-07-31", fetch=fetch)
    after = checkpoints.date_coverage(nse_archive.SOURCE)["days_done"]
    return after > before, {"days_before": before, "days_after": after}


def case_yahoo_prices() -> tuple[bool, Any]:
    result = prices.backfill(list(UNIVERSE), actor=ACTOR, limit=10, fetch=chart_fetcher())
    depths = {d["symbol"]: d["years"] for d in coverage.company_depth()}
    actions = {r["action_type"] for r in store.fetch("corporate_actions", limit=200)["rows"]}
    return (
        result["companies_done"] == 3 and depths.get("AAA", 0) > 20 and
        {"dividend", "split"} <= actions,
        {"companies": result["companies_done"], "rows": result["rows_written"],
         "deepest": result["deepest"], "actions": sorted(actions)},
    )


def case_statements_raw_only() -> tuple[bool, Any]:
    result = statements.backfill(list(UNIVERSE), actor=ACTOR, limit=10, loader=statement_loader)
    row = store.fetch("financials_annual", entity="AAA",
                      filters={"fiscal_year": "FY25"})["rows"][0]
    return (
        result["companies_done"] == 3 and row["revenue"] and row["free_cash_flow"] is None,
        {"companies": result["companies_done"], "annual_periods": result["annual_periods"],
         "derived_left_empty": row["free_cash_flow"] is None},
    )


def case_valuation_reconstructed() -> tuple[bool, Any]:
    result = valuation_history.reconstruct(list(UNIVERSE), actor=ACTOR, limit=10,
                                           cadence="quarterly")
    rows = store.fetch("historical_valuation", entity="AAA", sort="date", order="asc",
                       limit=500)["rows"]
    priced = [r for r in rows if r.get("pe")]
    return (
        result["companies_done"] == 3 and len(priced) > 20,
        {"companies": result["companies_done"], "observations": result["observations"],
         "aaa_points": len(rows), "aaa_with_pe": len(priced),
         "span": f"{rows[0]['date']} → {rows[-1]['date']}" if rows else None},
    )


def case_no_lookahead() -> tuple[bool, Any]:
    timeline = valuation_history._statement_timeline("AAA")
    fy25 = next((e for e in timeline if e["label"] == "FY25"), None)
    if not fy25:
        return False, "FY25 statement missing"
    # Any observation before FY25 became public must be using an earlier statement.
    early = [r for r in store.fetch("historical_valuation", entity="AAA", limit=500)["rows"]
             if r["date"] < fy25["known_at"]]
    leaked = []
    for row in early:
        used = valuation_history._latest_known(timeline, row["date"], quarterly=False)
        if used and used["known_at"] > row["date"]:
            leaked.append(row["date"])
    return (
        fy25["known_at"] > "2025-03-31" and not leaked,
        {"fy25_period_end": "2025-03-31", "fy25_public_from": fy25["known_at"],
         "observations_checked": len(early), "lookahead_violations": len(leaked)},
    )


def case_cross_sectional() -> tuple[bool, Any]:
    """Peers priced on the same day, ranked against each other — and stable on a re-run."""
    dates = sorted({r["date"] for r in store.fetch("historical_valuation", limit=3000)["rows"]})
    latest = dates[-1]
    repeat = valuation_history.rerank_dates([latest], actor=ACTOR)

    rows = {r["symbol"]: r for r in
            store.fetch("historical_valuation", filters={"date": latest}, limit=50)["rows"]}
    priced = {s: r for s, r in rows.items() if r.get("pe") and r.get("percentile") is not None}
    if len(priced) < 3:
        return False, {"on": latest, "priced": sorted(priced)}

    dearest = max(priced, key=lambda s: priced[s]["pe"])
    cheapest = min(priced, key=lambda s: priced[s]["pe"])
    have_median = [s for s, r in rows.items() if r.get("sector_median")]

    return (
        len(have_median) == 3
        # the most expensive name must sit at the bottom of the cheapness percentile
        and priced[dearest]["percentile"] < priced[cheapest]["percentile"]
        # reranking is idempotent: the same inputs write no new versions
        and repeat["rows_updated"] == 0,
        {
            "on": latest,
            "with_sector_median": have_median,
            "dearest": {dearest: round(priced[dearest]["pe"], 1),
                        "percentile": priced[dearest]["percentile"]},
            "cheapest": {cheapest: round(priced[cheapest]["pe"], 1),
                         "percentile": priced[cheapest]["percentile"]},
            "idempotent_rerun_updates": repeat["rows_updated"],
        },
    )


def case_series_reads() -> tuple[bool, Any]:
    series = history.series("AAA", "price", window="max")
    compare = history.compare(["AAA", "BBB", "CCC"], "price", window="max")
    as_at = history.as_at("AAA", "2012-01-01")
    stats = series.get("stats") or {}
    return (
        series["ok"] and stats.get("cagr_pct") is not None and compare["ok"]
        and as_at["price"] and as_at["price"]["date"] < "2012-01-01",
        {"points": series["count"], "cagr_pct": stats.get("cagr_pct"),
         "years": stats.get("years"), "percentile": stats.get("current_percentile"),
         "ranking": [r["symbol"] for r in compare["ranking"]],
         "as_at_2012_used": as_at["price"]["date"]},
    )


def case_coverage_board() -> tuple[bool, Any]:
    board = coverage.dashboard()
    summary = board["summary"]
    tables = {t["table"]: t["rows"] for t in board["tables"]}
    return (
        summary["companies_with_history"] == 3 and summary["max_years"] > 20
        and tables["historical_valuation"] > 0 and board["sectors"],
        {"companies": summary["companies_with_history"], "avg_years": summary["avg_years"],
         "max_years": summary["max_years"], "tiers": summary["tiers"],
         "valuation_rows": tables["historical_valuation"]},
    )


def case_engine_gate() -> tuple[bool, Any]:
    os.environ.pop("WAREHOUSE_BACKFILL_ALLOW_HERE", None)
    os.environ["AGI_ROLE"] = "web"
    blocked = engine.run(actor=ACTOR)
    os.environ["AGI_ROLE"] = "gather_worker"
    allowed = engine.worker_only()
    os.environ["WAREHOUSE_BACKFILL_ALLOW_HERE"] = "true"
    return (
        blocked.get("error") == "worker_only" and allowed is None,
        {"refused_on_web": blocked.get("error"), "allowed_on_worker": allowed is None},
    )


CASES: tuple[tuple[str, Callable[[], tuple[bool, Any]]], ...] = (
    ("archive_walks_backwards", case_walks_backwards),
    ("completed_days_never_refetched", case_no_repeat_downloads),
    ("backfill_resumes_after_interruption", case_resumes),
    ("yahoo_loads_decades_with_actions", case_yahoo_prices),
    ("statements_stored_raw_only", case_statements_raw_only),
    ("valuation_history_reconstructed", case_valuation_reconstructed),
    ("no_lookahead_in_any_observation", case_no_lookahead),
    ("cross_sectional_peer_ranking", case_cross_sectional),
    ("series_aggregates_at_query_time", case_series_reads),
    ("coverage_reports_real_depth", case_coverage_board),
    ("universe_backfill_is_worker_only", case_engine_gate),
)


def main() -> int:
    db.init(force=True)
    for name, fn in CASES:
        check(name, fn)

    passed = sum(1 for r in RESULTS if r["pass"])
    summary = {
        "suite": "historical_backfill_acceptance_v1",
        "cases": len(RESULTS),
        "passed": passed,
        "failed": len(RESULTS) - passed,
        "pass_rate_pct": round(100.0 * passed / max(len(RESULTS), 1), 1),
        "warehouse_rows": db.info().get("total_rows"),
    }
    print(json.dumps(summary, indent=2))
    for result in RESULTS:
        mark = "PASS" if result["pass"] else "FAIL"
        print(f"  [{mark}] {result['case']} ({result['ms']}ms) "
              f"{json.dumps(result['detail'], default=str)[:300]}")

    out = Path("/tmp/historical_backfill_acceptance_v1.json")
    out.write_text(json.dumps({"summary": summary, "results": RESULTS}, indent=2, default=str))
    print(f"wrote {out}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
