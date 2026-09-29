# NIFTY regime research v1

This adds seven **paper-only** strategies alongside the four unchanged benchmark accounts. There is no broker order endpoint, funded account access, or claim of a profitable edge.

## Portfolio and data

The seven new strategies share ₹100,000. Their zero-based equity/cash are attributed P&L/cash contributions; the shared marked equity is ₹100,000 plus all strategy contributions. Benchmarks remain independently funded and do not participate in this shared account. Never sum all eleven cards as one portfolio.

One Upstox V3 full stream supplies NIFTY spot, at most 42 nearby options, the nearest unexpired NIFTY future from the public instrument master when available, and pinned open/pending contracts. Spot never substitutes for a futures fill or futures VWAP. `marketFF.atp` supplies the futures' own average traded price. Quotes must have positive volume/OI, uncrossed bid/ask, one-lot displayed depth, and timestamps within five seconds; futures additionally require spreads ≤0.1%. Options use 2–14-calendar-day expiries. Missing futures metadata leaves only that strategy waiting.

Complete five-minute OHLC bars are sampled from one-second observations. Each minute requires ≥55 samples spanning its first/last seconds; partial bars are discarded. Up to 100 complete bars survive overnight, with 50 bars required for indicators and three new bars after a session/gap. Volatility breakouts need seven fresh bars. This is sampled data, not full exchange tick history. RV is withheld across missing five-minute intervals.

The near-expiry ATM-IV percentile requires 20 previous daily observations and retains 60. Values are recorded from the last completed observed bar of each day, including paused sessions. No missing history is fabricated. The changing expiry tenor makes this a proxy, not a constant-maturity volatility forecast. No IV/RV fair-value claim is made.

## Strategies and selection

Wilder ADX/ATR14, EMA20/50 and the last completed close define trends (ADX≥25). Range requires ADX<18 and IV percentile≥60. Compression is a previous six-bar range below 3×ATR, followed by a completed close outside that range. Breakout classification takes priority over trend classification. All thresholds are research assumptions.

1. Regime debit: confirmed trend with previous-bar EMA20 pullback and last-bar breakout; ATM long and OTM short.
2. Regime credit: trend, IV percentile≥60; opposite-side 15–20 absolute-delta short and further OTM hedge.
3. Iron condor: range/high IV; hedged call and put shorts at 15–20 delta.
4. Long straddle: volatility breakout, IV percentile≤40; matched ATM call and put purchases.
5. Long strangle: same filter with 15–20 delta OTM long call/put.
6. Iron fly: range/high IV within 60 minutes after a manually reviewed blackout ends; matched ATM shorts with outer wings. This does not assume capturing an IV collapse that already happened.
7. Futures trend: trend plus futures price above/below its own ATP in the signal direction. Full notional is reserved, so a full NIFTY lot generally cannot fit ₹100,000. No fictional broker margin or fractional lot is used.

This order is also deterministic admission priority when signals compete. Shared portfolio results reflect that priority; they are not seven isolated backtests. RSI, breadth/Bank Nifty, skew/term structure forecasts, and automatic event feeds are not implemented in v1.

## Calendar and lifecycle

Admin `POST /api/intelligence/options-lab/paper-agents/calendar` accepts `{date: 'YYYY-MM-DD', windows: [{start: timezone-aware ISO, end: timezone-aware ISO}]}`. The engine token and existing Node administrator gate protect it. Empty windows means an explicit reviewed clear date. Unknown/review-expired dates block research entries. Calendar edits cancel pending research signals. Blackouts or expired review trigger exits for markable open research positions. This calendar does not alter preserved benchmark rules.

New entries: 10:00–14:15 IST after warm-up. Session exits begin 15:15. Long-volatility/fly positions have 30-minute time stops; other research positions two hours. Pausing cancels pending entries while markable positions continue exit monitoring.

Signals at t require newer quotes on every leg within five seconds and basket timestamp skew ≤1 second. Baskets fill all-or-none at ask/bid plus adverse slippage (options 0.5%, futures 0.02%). Real partial fills are not simulated. Missing exit quotes/gaps preserve unresolved positions at their last mark and halt shared admission. There is no automatic reset or invented recovery fill.

## Costs and limits

Per-entry planned risk≤₹2,000; total open planned risk≤₹4,000; two open positions; four entries/day total and two per strategy; no shared contract overlap. Shared daily marked-loss trigger ₹3,000; it latches for the day and requests exits when executable. These are triggers, not guaranteed loss bounds.

Options' piecewise expiry payoff is evaluated at zero and every strike. Negative high-price payoff slope is rejected. Reserve equals calculated expiry loss plus entry fees; exit fees are additional. Long baskets use a 35% planned-risk stop and 50% risk target; credit baskets a 35% risk stop and 50% net maximum-reward target. Futures stop risk is 2×ATR×lot plus entry fees, target twice that; there is no capped maximum loss. Futures cash records fees and price-difference P&L rather than exchanging the full notional.

Estimated fee model checked 28 September 2026: ₹20 options brokerage, futures min(₹20,0.05% notional); STT sell 0.15% options premium / 0.05% futures turnover; NSE transaction 0.03553% / 0.00183%; SEBI 0.0001%; IPFT ₹0.01/crore; buy stamp 0.003% / 0.002%; GST18% on brokerage/transaction/IPFT. Before rounding and actual broker adjustments.

Sources: https://upstox.com/brokerage-charges/ ; https://upstox.com/developer/api-documentation/instruments/ ; https://upstox.com/developer/api-documentation/v3/get-market-data-feed/

## Evidence and deployment

The new module is additive under session `research`; existing journals, balances and strategy definitions are preserved. New positions record strategy version, classifier snapshot, signal time, entry/exit quotes, per-leg charges and reasons. The dashboard shows forward comparison and explicit waiting conditions. All-strategy replay supports the two original strategies on fifteen-minute snapshots and the other nine on recorded one-second frames. There is no historical/out-of-sample validation of the new suite yet; the unit tests validate implementation, not returns.

Validation: payoff endpoints, futures ledger, shared limits, overlap, calendar validation/expiry, complete-bar warm-up, daily-IV recording, stale/mismatched/all-or-none execution, loss-trigger exits, preserved migrations and subscriptions. Run `PYTHONPATH=. python -m pytest options_lab/tests tests/test_route_offload.py -q` inside `intelligence-engine` and the normal frontend build.


## All-strategy replay

The admin backtest endpoint now queues an isolated low-priority Python worker, returning immediately. One job is allowed at a time, bounded to 15 minutes and 350,000 recorded frames. Progress and the last completed result persist in SQLite; the browser polls the existing private dashboard. Failed or interrupted jobs do not overwrite the previous completed result. No replay writes forward balances, positions, source quotes, or the live calendar.

The nine newer agents reuse `spread_agents.advance` and `regime_agents.advance` exactly. Earlier recorded frames warm indicators with entries disabled. Daily IV seeds are restricted to observations preceding the earliest replayed day, excluding future/test-day observations and preventing duplicate warm-up days. Raw frames are paged in bounded batches to keep memory down. A fixed final timestamp excludes later arriving data. No 15-minute-to-1-second interpolation, fabricated bid/ask sizes, delta, futures price or forced terminal exit is allowed.

All eleven agents appear in one comparison. Missing prerequisites produce `insufficient_data` and null performance metrics, not zero-profit backtests. Open/unresolved terminal positions are labelled incomplete and retain their last known marks. Zero trades with usable inputs remains an observed zero-trade result. Cost models and sampling intervals are visible; legacy results and shared strategy contributions are not independently comparable accounts.

Calendar edits now append timestamped audit records. Replay applies a review only when it was known at the simulated time. Optional `calendars` inputs accept dated, explicitly reviewed windows within the test range; an explicit empty window list means clear. These retrospective inputs are clearly labelled and affect only that run. Missing dates fail closed. Current session calendars are never silently copied into historical dates.

Historical Upstox OHLC candles do not contain the one-second depth/basket timing required by these rules. See https://upstox.com/developer/api-documentation/get-expired-historical-candle-data/. Existing raw evidence is retained for fourteen days; this release does not acquire or invent earlier high-frequency history. Performance must be reported only for available evidence, and implementation tests are not evidence of profitability.

## Daily IV bootstrap (29 September 2026)

The audited bundle in `options_lab/reference_data/nifty_atm_iv_history.json` supplies prior
completed daily ATM observations derived from public NSE F&O bhavcopies. Each
record keeps its source URL, SHA-256 of the NIFTY source rows, retrieval time,
selected expiry/strike, call and put closes/IV, forward quality and rate assumption.
Only the nearest 2–14-day expiry and a matched ATM pair qualify. Missing pairs,
nontraded contracts, low/medium quality forwards and excessive call/put IV
disagreement are excluded. The reusable acquisition command is
`PYTHONPATH=. python scripts/bootstrap_nifty_iv.py --as-of YYYY-MM-DD --output /tmp/iv.json`.

This is a labelled Black-76 end-of-day proxy (5.25% rate assumption), combined
with provider live IV; tenor and provider/model basis differences remain. It is
not India VIX, a constant-maturity index, or evidence of past trading returns.
Upstox V3 decimal IV is now converted to percentage points at ingestion; original
raw stored frames remain immutable and replay normalizes them when reading.
Earlier forward daily observations retain their original IV alongside a unit
correction. Accounts, open positions, past trades and risk limits are preserved.

The stream loads the bundled series locally and merges it once per IST day. No
historical network request runs inside the one-second execution loop. Completed
forward observations extend the daily series automatically; days deduplicate,
retain at most 60 observations within 120 calendar days, and require the most
recent observation to be no older than 10 calendar days. Stale history fails closed.
Historical imports are eligible only after their actual retrieval timestamp; a
replay before retrieval cannot claim the engine possessed this history earlier.
No prior performance is silently restated.
