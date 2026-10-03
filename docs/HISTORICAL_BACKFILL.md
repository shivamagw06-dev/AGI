# Historical Backfill & Time-Series Engine (Phase 7.1a)

Phase 7.0 built the warehouse tables. This phase fills them.

No new schemas. The eight historical tables the intelligence layer needs already
exist as warehouse tabs; what was missing was depth. Before this phase the
warehouse held 2,700 companies with three days of prices and a single valuation
snapshot. This phase makes those tabs accumulate.

- **Package** `intelligence-engine/institutional_warehouse/backfill/`
- **Reads** `intelligence-engine/institutional_warehouse/history.py`
- **Admin page** `/admin/historical-coverage`
- **Acceptance** `intelligence-engine/scripts/historical_backfill_acceptance_v1.py`

---

## The bug this phase exists to fix

The bhavcopy collector asked for the current day on every cycle and stopped at
the first success. Over 410 cycles it downloaded **406 files covering 3 trading
days** — the 30 July file alone 248 times — and consumed 147 MB doing it. A
worker that ran for weeks produced no price history at all.

Two changes:

1. The live collector now compares the payload checksum against the one it
   already holds and reuses the stored file instead of writing a duplicate.
2. A separate **archive walker** goes the other way: newest missing day first,
   then the day before, checkpointing each one. A completed day is never fetched
   again, and a day the archive does not have is retired after three attempts.

---

## Sources

| Stage | Source | Gives |
|---|---|---|
| `nse_archive` | NSE bhavcopy archive | Full-universe OHLCV, VWAP, delivery %, one file per trading day |
| `yahoo_prices` | Yahoo chart API | 20–30 years of daily OHLCV, adjusted close, dividends, splits |
| `yahoo_statements` | yfinance | ~4 annual years and ~4–6 quarters of raw statement lines |
| `valuation_history` | the warehouse itself | Point-in-time valuation observations |

Every source takes an injectable fetcher, so the engine is tested against
recorded payloads and exercises the same parsing code that runs on the worker.

---

## Resumability

Progress lives in the database, not the process.

| Table | Holds |
|---|---|
| `wh_backfill_dates` | one row per (source, trading day) — done, failed, attempts |
| `wh_backfill_checkpoints` | one row per (stage, company) — cursor, attempts, rows written, last error |
| `wh_backfill_jobs` | every run, its parameters, its stats and its errors |

A run does a bounded slice and stops. The next run continues from where it
stopped. Kill the worker mid-pass and nothing is lost or repeated.

---

## Point-in-time valuation

This is the part that makes historical questions honest.

For each observation date the reconstruction uses the price on that date and
**only statements that had already been published by then**. Every fiscal period
carries an availability date: period end plus a reporting lag, 60 days for
annual and 45 for quarterly.

```
FY25 annual   period ends 2025-03-31   public from 2025-05-30
FY25 Q2       period ends 2024-09-30   public from 2024-11-14
```

So a valuation dated April 2025 is built on FY24, because FY25 did not exist in
the market's hands yet. Without that rule every historical band is quietly
contaminated by information nobody had at the time, and a backtest built on it
looks better than reality.

Trailing twelve-month figures are used when four quarters were public; otherwise
the last published annual figures, so annual-only filers still get a multiple.

After the per-company pass, a **cross-sectional pass** prices each company
against the peers trading on the same day and writes the sector median, industry
median and percentile. Only the warehouse can compute that — it needs the whole
market on one date.

Observations are stored. Trends are not: CAGR, percentile-through-time and bands
are computed at query time in `history.py`, so they always reflect what the
warehouse currently holds.

---

## Screening

Beyond the warehouse's row-level validation, a series is screened as a series.

**Rejected** — impossible price (zero or negative), low above high, negative
volume, duplicate date within the series, future date, unparseable date,
invalid symbol.

**Warned** — a move beyond 60% in a day, and specifically an *unexplained price
break*: a move large enough to look like a split with no corporate action on
record for that date. That is usually a data error, not a market event.

`chronology_report` describes a stored series: span, point count and its largest
holes.

---

## Historical reads

No new schemas — these are query shapes over the existing tabs.

```
GET /v1/history/company/{symbol}?window=10y
GET /v1/history/series/{symbol}/{metric}?window=max
GET /v1/history/as-at/{symbol}?on=2020-03-31
GET /v1/history/table/{tab_id}?symbol=…&start=…&end=…&fiscal_year=FY24&quarter=Q2
GET /v1/history/compare?symbols=A,B,C&metric=price&window=5y
GET /v1/history/coverage/{symbol}
```

Windows: `1y`, `3y`, `5y`, `10y`, `20y`, `max`. Metrics span price, volume,
market cap, the multiples, the statement lines and the ratios.

Every series response carries aggregates computed on the spot: first, last, min,
max, median, average, change, CAGR, span in years and where the current value
sits in its own history.

---

## Coverage

`/admin/historical-coverage` reports what the warehouse actually holds: depth
tiers, rows and span by table, average years by sector, the deepest and
shallowest names, recent jobs, and the failures worth attention. It can also run
a bounded slice and inspect any single company.

It also reports **what the reconstruction could not build and why**. On the
current data that reads:

```
observations                3,316
with P/E                     23.7%
with P/B                      3.4%
with market cap               0.5%
share count on file        0 of 79 companies
```

That is not a bug in the reconstruction. The Knowledge Factory statement series
carries no share count, and market cap, book value and enterprise value all need
one. Rather than guess, those columns stay empty and the board says so. The
Yahoo statement backfill does carry `Ordinary Shares Number`, so this resolves
as soon as the worker can reach Yahoo.

---

## Running it

The backfill is **worker-only**. A universe pass is thousands of HTTP calls and
must never sit in front of Ask, so the engine refuses to run unless
`AGI_ROLE` is a worker role, or `WAREHOUSE_BACKFILL_ALLOW_HERE=true` overrides
it deliberately.

| Setting | Purpose | Default |
|---|---|---|
| `WAREHOUSE_BACKFILL` | Run slices on a timer in the gather worker | `true` on the worker |
| `WAREHOUSE_BACKFILL_INTERVAL_MIN` | Minutes between slices | `30` |
| `WAREHOUSE_BACKFILL_COMPANIES` | Companies per slice | `25` |
| `WAREHOUSE_BACKFILL_DAYS` | Trading days per slice | `40` |
| `WAREHOUSE_BACKFILL_ALLOW_HERE` | Override the worker gate | `false` |

```bash
# one slice, by hand
cd intelligence-engine
AGI_ROLE=gather_worker PYTHONPATH=. python3 -c "
from institutional_warehouse.backfill.engine import run
print(run(actor='ops', companies=50, days=90))"
```

Filling 3,000 companies takes many slices. That is the design: bounded work,
checkpointed, resumed on the next tick, so coverage climbs without a single
long-running job that fails at hour six.

---

## Tests

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest institutional_warehouse/tests -q

INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_hist PYTHONPATH=. \
  python3 scripts/historical_backfill_acceptance_v1.py
```

The acceptance suite proves the phase against recorded sources: the walker goes
backwards, a completed day is never refetched, an interrupted run resumes, Yahoo
loads decades with dividends and splits, statements land raw, valuation is
reconstructed with no lookahead, peers are ranked cross-sectionally, series
aggregates compute at query time, coverage reports real depth, and a universe
backfill refuses to run outside the worker.

---

## Known limits

- **Yahoo statements are shallow** — about four annual years. Deep statement
  history needs Capital IQ exports or filings, which append alongside because
  every row is keyed by period and carries its own source.
- **Reporting lags are conventions, not filings.** A company that reported late
  will be treated as having reported on the lag date. Exact filing dates would
  need the announcement feed.
- **Yahoo rate-limits hard.** `pause_seconds` and small slices exist for that
  reason; a full universe pass is a background campaign, not a single run.
- **The archive walker cannot invent history the archive does not serve.** NSE's
  full bhavdata files begin in 2016; older years come from the zipped archive
  and Yahoo.
