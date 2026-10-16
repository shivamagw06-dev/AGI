# Live Alpha publication archive

The new archive starts on deployment. `published_at` is the database clock when the composite becomes available in the server store, not a customer page-view or execution timestamp. Facts are append-only. A source key plus per-symbol head and transaction advisory lock deduplicate repeated evaluations. Neutral/reversed directions close the prior episode; weakening, strengthening (15 score points from the last logged baseline) and component changes append events. The five intraday engines retain their existing rules. Daily equity/sector screens are separate models, not archived as these composite calls.

The publisher requires the four core engines to persist successfully, with optional derivatives participation, and rejects stale/replayed evaluations. Missing engines do not silently withdraw prior calls. Original quote time, raw price, benchmark, components and quality are preserved. Null or old quote times are visible. New broker execution is not connected.

## Price follow-up and simulation

- 15 minutes / 1 hour count trading minutes. Close and 1/5/20-day windows use NSE sessions/holidays.
- Close-based price measurements wait for published historical daily candles. Minute measurements use captured quotes or past one-minute candles within 60 seconds of the due timestamp.
- Missing prices remain pending, then missing after seven days. Final measurements cannot be rewritten.
- Stock change is `(price / reference - 1) * 100`. Directional change reverses the sign for negative calls; it is not the return from buying that stock. Conflicting calls have no directional simulation.
- Hypothetical holding-period returns require a fresh original reference and the first eligible recorded post-publication bid/ask within five minutes, with exchange and receipt freshness, uncrossed depth and spread <=2%. They use the ask to buy and bid to sell, plus 5 bps slippage each side and 10 bps round-trip fees. Short borrow/financing are excluded. Each horizon is an independent hypothetical holding period, not an executed strategy trade. The exit horizon is the first recorded reversal/withdrawal.
- Daily charts use unadjusted closes. Dividends and corporate actions are not reconciled, so charts are price changes, not total returns. Gaps stay null. The chart currently fetches at most 260 trading sessions per record. Full-cohort summaries count overlapping publications; they are not portfolio returns.
- Market-quote snapshots already retained by the feed are reused. A single sequential worker runs every minute; daily history uses the existing shared rate-limited candle book. No additional paid services.

## Earlier data

An earlier date shows the last stored in-session snapshot per engine, not all intraday publications. Publication time is unknown. Original price is reconciled to a historical candle within 3%; if unavailable/inconsistent, percentage returns are withheld. Matching a candle does not prove publication or tradability. Hypothetical entry/trade results are never backfilled for these records.

## Security and verification

All six new tables have RLS enabled and no browser-role privileges. REST reads and writes use the existing server service credential. Functions are security-invoker with empty search paths, callable only by the service role. No credentials reach the frontend. Informational RLS-without-policy advisor findings are intentional for these server-only tables.

The production migration was applied before application deployment. Transaction-rolled-back assertions verified idempotency, immutable publication prices, reversal logs and exit scheduling; the test left zero publications. Unit tests cover displayed-score parity, holidays, timestamp/depth rejection, short/long arithmetic, null prices, official-close settlement, missing outcomes, filters, caches and one-to-one entry relations.
