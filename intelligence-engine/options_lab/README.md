# Pricing Engine V1 live validation

Status: promising validated prototype; extended validation pending.

This package keeps the frozen Black-Scholes implementation unchanged and adds
the live evidence pipeline around it:

1. Fetch the Upstox NIFTY option chain every 15 minutes during NSE hours.
2. Retain each individual contract's latest IV in SQLite.
3. Reprice that contract at the next observed NIFTY spot using the prior IV.
4. Store the predicted and actual prices as an immutable validation observation.
5. Generate daily and cumulative Markdown/JSON reports after 15:45 IST.

This validates conditional repricing. It does not forecast NIFTY direction,
future IV, option direction, or trading profitability.

## Upstox inputs

The implementation uses the option contracts endpoint for expiry, strike, and
lot size, and the option chain endpoint for spot, bid/ask, LTP, volume, OI, IV,
and Greeks.

Official documentation:

- https://upstox.com/developer/api-documentation/get-option-contracts/
- https://upstox.com/developer/api-documentation/get-pc-option-chain/

## Configuration

Required environment variable:

    UPSTOX_ACCESS_TOKEN=...

Alternatively, point to a token file that can be rotated without restarting:

    UPSTOX_ACCESS_TOKEN_FILE=/secure/path/upstox-token

Optional environment variables:

    OPTIONS_LAB_DB_PATH=./data/options_lab.sqlite3
    OPTIONS_LAB_REPORT_DIR=./artifacts/options_lab
    OPTIONS_LAB_UNDERLYING_KEY=NSE_INDEX|Nifty 50
    OPTIONS_LAB_UNDERLYING_SYMBOL=NIFTY
    OPTIONS_LAB_STRIKE_WINGS=10
    OPTIONS_LAB_MAX_EXPIRIES=4
    OPTIONS_LAB_MAX_DTE_DAYS=30
    OPTIONS_LAB_RISK_FREE_RATE_PCT=5.25
    OPTIONS_LAB_MAX_VALIDATION_HORIZON_MINUTES=30

Credentials are read at collection time and are never written to SQLite,
reports, logs, or raw snapshot JSON.

## Commands

Run from the intelligence-engine directory:

    python -m options_lab.automation init
    python -m options_lab.automation status
    python -m options_lab.automation collect
    python -m options_lab.automation report --date YYYY-MM-DD
    python -m options_lab.automation run

The run command is the automation entrypoint. It collects at most once per
15-minute bucket from 09:15 through 15:30 IST on weekdays and creates the daily
report after 15:45 IST. SIGTERM and SIGINT stop it cleanly.

For persistent cloud operation, point the database and report directory to a
persistent disk before starting the worker.

## Frozen validation protocol

Headline metrics:

- Observation-weighted MAPE.
- Day-weighted MAPE.
- MAE and median absolute error in option points.
- Day-clustered 95% confidence interval.
- Percentage within max(5 points, 10% of actual premium).

Reports break errors down by premium, moneyness, DTE, expiry, and option type.
The report remains extended_validation_pending until at least 60 trading days
exist. It passes only when both observation-weighted and day-weighted MAPE are
below 3%.

August 17-21, 2026 remains a permanently burned historical holdout. Live
observations collected by this worker form the prospective evidence set.

## NIFTY paper agents (v1)

Admin desk: `/admin/nifty-paper-agents`. Two independently funded INR 100,000
virtual accounts evaluate opening-range breakout and rolling-mean reversal.
These are hypotheses, not the "best" Indian strategies or proven edges.

- Breakout uses all three 09:15/09:30/09:45 spot samples, then a 0.1% break.
- Reversal uses six strictly earlier samples, a two-population-standard-deviation
  displacement and a minimum 0.2% distance. Neither strategy optimizes thresholds.
- Choose the nearest expiry 2–14 calendar days out, then nearest strike. Buy one
  whole CE/PE lot at the *next* recorded ask plus 0.5% assumed slippage. Require
  positive volume/OI and bid/ask with no more than 5% spread. Instrument metadata
  supplies lot size; no static lot-size assumption.
- Exit at an observed bid minus 0.5% on 20% premium loss, 40% premium gain,
  INR 2,000 marked daily loss, or the first sample at/after 15:15 IST. No new
  signals from 14:15, no fills from 14:30. Max two entries/day and INR 10,000
  premium plus entry-cost budget. Stops are observations, not guaranteed fills.
- All-in cost stress is INR 20 + 0.5% premium turnover *per side*. This is an
  explicit illustrative assumption, not a verified statutory/broker tariff.
  No short-option margin assumptions or real orders are involved.
- Replay reads only stored Upstox NIFTY snapshots (max 60 calendar days/250,000
  rows). It never substitutes spot candles or Black-Scholes prices for option
  fills. Empty history is reported as no data. Historical replay is exploratory,
  not an out-of-sample claim. Test frozen settings on unseen future data before
  drawing any conclusion. Report dates/coverage alongside any metrics.
- Collection timestamps are not exchange timestamps. Fifteen-minute observations
  miss intrabar excursions and cannot verify executable depth or actual fills.
  Missing quotes/gaps over 20 minutes with an open position halt that account;
  no fabricated closing trade is added. Unresolved positions remain at their
  last known mark, so closed P&L is incomplete when positions are unresolved.
- Start creates a durable account from that moment; restarting the worker cannot
  double-process a quote. Pause cancels pending entries but keeps exit observation
  active. Resume does not erase history or unblock unresolved positions. Review
  an unresolved account's source data before any explicit future reconciliation.

Architecture: source `option_snapshots` → deterministic strategy decision → next
quote paper fill → risk/exit observation → immutable completed-trade records in
session state. State/cursor writes use one SQLite transaction in the separate
`nifty_paper_agents.sqlite3` alongside the evidence DB. Historical replay results
are separate and cannot alter forward paper accounts. Source quotes are read-only.
The existing collector calls `tick()` after each successful collection; no new
poller, Upstox subscriptions, broker account permissions, or credentials are needed.

APIs under `/api/intelligence/options-lab/paper-agents` are administrator-only:
GET status; POST `/control` with `start`/`pause`; POST `/backtest` with ISO start/end.
The engine endpoints also require the internal engine token. The module has no
broker/network client and does not call order endpoints. Public visitors cannot
view or start these private simulations.

Primary data documentation checked for this implementation:
https://upstox.com/developer/api-documentation/get-pc-option-chain/
https://upstox.com/developer/api-documentation/expired-instruments/

Expired instrument candles are a separate data product/capability; this v1 does
not imply that historical bid/ask chains can be reconstructed from those candles.

Paper agents v1.1 sample the first collection in each 15-minute window, so duplicate collectors or retries cannot accelerate signals/fills. Opening range requires all three distinct opening windows. Replay displays the actual sampled count separately from raw stored batches.

## One-second forward paper worker (v2)

`python -m options_lab.streaming` is a separate, read-only Upstox V3 WebSocket
process. Production `scripts/start_engine.sh` enables it with the existing
options-lab service; set `NIFTY_PAPER_STREAM_ENABLED=false` to opt out. There is
no broker order code. The existing Start/Pause controls still govern entries.
The 15-minute collector no longer writes forward account transitions in stream
mode. Its pricing validation and historical replay are unchanged.

- One `full` subscription: NIFTY index + nearest expiry 2–14 days away, nearest
  42 CE/PE contracts. Refresh the strike selection every five minutes and retain
  every open/pending contract. Metadata supplies actual lot sizes.
- One-second monotonic evaluation loop; never burst to catch up a delayed loop.
- Require Upstox `NSE_FO=NORMAL_OPEN`, local weekday session, per-instrument
  provider timestamps no more than five seconds old, a fresh NIFTY observation,
  valid spread/volume/OI and displayed best-bid/ask size covering the whole lot.
  Timestamps identify feed updates, not guaranteed exchange-tick latency.
- Entry requires a strictly newer feed quote than the signal's quote. Disconnects
  cancel pending signals; missing/stale observations freeze existing positions
  unresolved and halt that agent. No interpolated fills or automatic halt resets.
- Indicator context remains first fresh observation within 30 seconds of each
  15-minute boundary. Mean reversion uses six strictly prior boundary samples;
  OR needs the 09:15, 09:30, 09:45 observations. A midday start cannot invent them.
- Account/state + compressed one-second frames commit atomically to the existing
  durable SQLite database each second. Only new `second_frames` older than 14
  calendar days are pruned. Trade journals, balances and old validation evidence
  are retained. Frames include source quote timestamps, so cached quotes are not
  represented as newly received ticks. The UI's replay remains 15-minute only.
- Migration preserves balances/trades, clears pending signals and warms up fresh
  indicator context. Any legacy open position stays unresolved/blocked.
- Advisory disk lock prevents simultaneous stream workers. TLS remains verified;
  exponential reconnect up to 60 seconds reloads the token. URLs/tokens and raw
  connection exception messages are never logged. A post-close startup checks
  authorization/subscription then disconnects until the next weekday session;
  exchange feed status additionally prevents holiday trading.
- Dashboard (5-second refresh) reports recent CPU as % of **one core**, peak RSS,
  processing milliseconds, fresh/subscribed contracts and worker heartbeat.
  These are process metrics, not total-server utilization. Counters reset on
  worker restart; evidence and accounts do not.

Official protocol (downloaded 2026-09-28):
https://assets.upstox.com/feed/market-data-feed/v3/MarketDataFeed.proto
https://upstox.com/developer/api-documentation/v3/get-market-data-feed/
Generated with grpcio-tools 1.71.0 / protobuf 5.29; vendored schema and decoder in
`options_lab/proto/`. Regenerate with `python -m grpc_tools.protoc` using that
folder as both include and Python output directory. No compiler is needed at
runtime.

### Additional forward paper agents (spread experiments v1)

Two independent ₹100,000 accounts are added without resetting legacy accounts.
`trend_pullback` uses completed 5-minute spot candles: 3/10-close average trend,
>0.1% six-close move, prior-bar pullback through the prior three-close average,
then a close beyond the prior bar's high/low. Buy ATM and sell further OTM CE/PE.
`volatility_credit` uses the same directional trend (0.1–0.6%), last-bar range
<=0.4%, and same-expiry ATM option IV >= max(12%, 1.25 × annualised intraday RV).
RV uses 11 five-minute returns, scaled by 75×252. This is a short-history proxy,
not a calibrated same-horizon volatility forecast. Sell an option >0.3% OTM on
the opposite side of the trend and buy a further OTM hedge. Missing IV means no trade.

Candles are **one-second sampled spot OHLC**, not all exchange ticks; no spot
VWAP or invented volume. A minute needs >=55 observations, first within 2sec,
last within 3sec; five consecutive complete minutes form a 5-minute candle.
12 consecutive complete candles warm up each day or after a data gap. No
unfinished candle is eligible. Entry window 10:15–14:15 IST; session exits at 15:15.
Nearest eligible expiry is 2–14 days away; strikes 50–200 points apart (50 preferred).
All thresholds are fixed research hypotheses, not optimised profitability claims.

Entry needs newer two-sided quotes on BOTH legs, <=5sec age, <=1sec quote skew,
full lot size at best bid/ask, correct lot/expiry, <=5% bid/ask spread. Both legs
fill or neither does; partial-fill/unhedged real execution is NOT modelled.
Adverse 0.5% slippage on every leg entry/exit. Missing exits freeze BOTH legs and
halt that account; no future backfilled exit is fabricated. Pin both held legs.

Max planned expiry loss incl. entry fees ₹2,000; exit costs additional. Two entries
per day and ₹2,000 daily loss trigger. Debit stop 40% of debit; target 50% of remaining
expiry gross upside. Credit target 50% of credit; stop=min(half gross maximum loss,
credit). Stops compare whole-spread net liquidation P&L and may overshoot.
Paper capital reserve = strike width×lot + gross long premium + entry fees.
This fully funds the model spread liability but is NOT broker SPAN/exposure margin
or a promise ₹1 lakh suffices for live orders. Refuse if reserve exceeds account cash.

Dated new-agent fee model from https://upstox.com/brokerage-charges/ and
https://www.nseindia.com/static/products-services/equity-derivatives-securities-transaction-tax
(checked 28 September 2026): ₹20/order, sell-premium STT 0.15%, NSE premium transaction
charge 0.03553%, SEBI ₹10/crore, buy stamp 0.003%, IPFT ₹0.01/crore, GST 18% on brokerage,
transaction and IPFT. Estimates before broker rounding; exclude expiry/exercise
charges because no expiry-day entries. Legacy agents keep their original
illustrative fees; their results are explicitly labelled and should not be
compared as if they share this fee model.

Existing 15-minute historical replay remains legacy-only. New strategies need
forward one-second data; do not fabricate historical spread results from slow snapshots.

### Official daily Nifty research

The admin paper desk includes four separate **daily index-direction reference studies**:
EMA50/200 trend, 20/10-session channel breakout, RSI2 pullback above EMA200,
and 63-session momentum with an EMA200 regime filter. They do not place orders
or add options positions to the eleven intraday agents.

`daily_research.py` accepts official NSE historical CSVs and the daily all-index
report. The initial `reference_data/nifty_daily_ohlc.json` contains 743 rows
captured from the NSE Indices Historical Data UI (29 September 2023–28 September
2026), with source, retrieval time and a normalized-content SHA-256. Admin
uploads are labelled as uploader-asserted provenance. Conflicting dates are
rejected for review, not silently overwritten. Reports use the persistent
paper-research database and merge the seed once by its content hash.

There are 400 completed sessions of warm-up; every decision uses only the
previous close and earlier data and executes at the next observed open. The
comparison stops at the final observed open, charging that open's rebalance.
Latest-close signals are shown separately. Exposure is a synthetic daily
rebalanced +/-1x index reference, with 5 bps per exposure leg and 10 bps stress.
Dividends, financing, broker margin, options decay, derivatives prices and live
fills are not simulated. These are retrospective studies, not held-out evidence.
A gap over seven calendar days restarts warm-up; smaller missing-session gaps
are not independently audited. Insufficient history produces no return figure.

Engine routes `/v1/options-lab/daily-research`, `/import`, and `/refresh` require
the internal engine token; the Node proxy requires a verified administrator.
Calculations and downloads run off the event loop. The refresh action requests
one fixed prior-calendar-day official report and retains cached data on failure
(including weekends or a report that has not been published). There is no public
website polling scheduler. Continuous direct exchange collection requires an
authorised feed; this importer does not replace the existing Upstox intraday feed.

### One-minute approximate backtest (separate experiment)

`GET/POST /v1/options-lab/minute-backtest` is token-protected; the website proxy
also requires the strategy-lab administrator. Requests accept `start`, `end`
(completed dates, up to 180 calendar days), and explicit retrospective `calendars`
in the detailed replay format. A bounded, low-priority subprocess downloads and
caches Upstox V3 spot minute bars and expired F&O minute OHLCV/OI. Expired history
requires Upstox Plus. A job is limited to one hour and 3,500 contract requests;
retries reuse completed downloads. Only returned expired expiries are available.
The collector adds 45 prior calendar days for warm-up and rolling estimated IV.

Results use `mode=one_minute_approximate` and their own SQLite job/result store.
They never enter `second_frames`, `backtests`, or forward account state. All nine
newer strategies are separate ₹1 lakh accounts in this approximation, unlike the
shared forward research account. Signal selection reuses the five-minute rules;
execution is a deliberately separate candle model. Entry at the next minute open;
minute-close stop/target/time checks exit at the following open. No intra-minute
ordering or market depth is invented. Basket fills assume all legs execute.
BSM-estimated IV/delta use 5.5% rate and zero dividend yield. Futures average traded
price is approximated by cumulative typical-price × volume / volume. Current fee
rates apply throughout history; stress actually reruns with twice slippage/fees.
Open/missing-exit positions suppress headline P&L; the export retains closed-only
results, positions, skips, trade legs, fees, source coverage and all assumptions.
Missing dated event reviews block research entries rather than assuming no events.

### Recorded evidence: 365-day retention

Recent 14 UTC days stay in the SQLite hot store; older full days move to lossless
`nifty_second_archive/YYYY-MM-DD.jsonl.gz` beside `OPTIONS_LAB_DB_PATH`. Every
archive is read back, its row count/content hash verified, then durably renamed
with a SHA256 manifest before any hot rows are removed. Archive failure retains
hot evidence. Compression runs in a low-priority subprocess, outside the trading
transaction. A file lock prevents detailed replay racing archival/pruning. Replay
merges verified archived frames with recent records and deduplicates timestamps;
it remains limited to 60 calendar days/1.5 million frames/15 minutes per job.
Archives expire after 365 days. The UI exposes archive size/free space and errors.

This requires a **persistent evidence volume**. Archives on the same volume are
not disaster-recovery backups. Monitor volume capacity and take independent
backups; no paid storage subscription is created by this change. Previously
pruned data cannot be recovered. If free space is below 512 MiB, archival fails
closed and retains hot rows; operators must increase space before collection
runs out. Cached minute history also shares this volume.
