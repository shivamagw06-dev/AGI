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
