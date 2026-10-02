# Portfolio price snapshots

Read-only Yahoo history collection; no broker orders or DB mutations. The reviewed instrument map is independent of portfolio weights. Never select the first search match automatically; verify the listing/share class and record evidence in instruments.json. Four ambiguous copied holdings are intentionally unmapped.

Manual refresh from repo root:

```
python3 scripts/portfolio-history/collect.py --cutoff YYYY-MM-DD
node scripts/portfolio-history/report.mjs /path/to/current-public-portfolio-catalog.json
node --test src/lib/portfolioHistory.test.js
npm run build
```

Use the latest fully completed US session, not today's partial bar. The collector defaults to yesterday's New York date, stores raw responses in /private/tmp/agi-portfolio-history/raw/<cutoff>, and fetches ~13 months in two bounded workers. --refresh bypasses that dated cache. TLS verification remains enabled. Failed histories are explicit, not replaced by older data. Benchmark failure/staleness preserves the old output and fails the run. Commit generated public/data files only after reviewing coverage. No automatic refresh schedule has been installed.

The download includes reviewed holdings, research-candidate tickers (not allocated), and SPY for the session calendar. Four columns: exchange-local date, provider adjusted close, provider close, volume. Currency, exchange, provider identity, corporate-action payloads and source URLs accompany each series. No prices are fabricated or forward-filled.

Portfolio results: initial current weights × adjusted price ratios, held without rebalancing; corporate distributions are represented by adjusted close (not added twice). Calendar-month boundaries use the last SPY session on or before the boundary. Same dates and all sessions required for each holding. Missing/invalid data or an incomplete allocation withholds full results. Tiny rounding totals within 100 ±0.05 are normalised explicitly. Unweighted candidates are excluded; zero weight has no effect. New tickers/changed names require a mapping and refreshed history. Exact-symbol mismatch invalidates the old mapping.

This is a retrospective current-allocation simulation (look-ahead and survivorship bias), not Vested/AGI realised performance. USD gross returns exclude fees/taxes/FX. No independent corporate-action reconciliation or intraday drawdown. A seven-day stale warning is displayed. The standalone comparison report is a dated snapshot; the interactive detail page uses the current catalog.
