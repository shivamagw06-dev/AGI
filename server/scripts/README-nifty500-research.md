# Nifty / NSE equity research worker

The research worker generates derived technical research for the configured equity universe and publishes a fully populated run to Supabase. It does not publish raw Groww market data, recommendations, targets, or order instructions.

## Universe files

| File | Scope |
|------|--------|
| `NIFTYstocks.csv` | **All NSE cash equities** (~2,300 EQ/BE/SM) — preferred when present |
| `Nifty500.csv` | Nifty 500 constituents (~500) — fallback |

Refresh the full NSE book from the official exchange list:

```bash
python3 server/scripts/refresh_nifty_stocks.py
```

## Required environment variables

```bash
GROWW_ACCESS_TOKEN=...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
# Optional explicit path (defaults to NIFTYstocks.csv when that file exists)
NIFTY500_CONSTITUENTS_PATH=/opt/render/project/src/NIFTYstocks.csv
# Full NSE runs default to 0.85 coverage; raise/lower as needed
NIFTY500_MINIMUM_PUBLISH_COVERAGE=0.85
# Optional pacing + smoke limits
NIFTY500_REQUEST_DELAY_SEC=0.15
# NIFTY500_SYMBOL_LIMIT=25
```

The service-role key is server-only. Never use it in a `VITE_` variable, browser code, or public client.

## Run once (full NSE analysis)

```bash
cd server
pip install -r requirements.txt
python3 scripts/nifty500_research_engine.py --once
```

Smoke test a small slice:

```bash
NIFTY500_SYMBOL_LIMIT=25 python3 scripts/nifty500_research_engine.py --once
```

## Troubleshooting: `Saved 0 research records` / `0.0% coverage`

`Ready to Groww!` only means the SDK constructed. If every symbol then fails:

1. Pull the latest `nifty500_research_engine.py` — history now uses Groww’s **`get_historical_candles`** (`groww_symbol` + `1day`), not the deprecated `/historical/candle/range` path that often returned empty/truncated series.
2. Re-run a smoke slice and read the per-symbol `REJECT` / `ERROR` lines (and the final “top reasons” summary).
3. Confirm `GROWW_ACCESS_TOKEN` is a fresh Trading API access token with historical/backtesting access.
4. Confirm `server/.env` has `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (publish still runs after analysis).

## Run as a Render background worker

```bash
cd server && pip install -r requirements.txt && python3 scripts/nifty500_research_engine.py
```

The default schedule is `16:15` IST on weekdays. Configure optional runs with:

```bash
NIFTY500_SCHEDULE_TIMES_IST=08:30,12:30,16:15
```

Deploy the Supabase migration `supabase/migrations/20260723133739_nifty500_research.sql` before starting the worker. A run remains private until stock records were written successfully; then it becomes the single public current run.
