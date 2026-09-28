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
