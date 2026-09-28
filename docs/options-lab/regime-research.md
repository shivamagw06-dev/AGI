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

The new module is additive under session `research`; existing journals, balances and strategy definitions are preserved. New positions record strategy version, classifier snapshot, signal time, entry/exit quotes, per-leg charges and reasons. The dashboard shows forward comparison and explicit waiting conditions. Historical replay continues to cover only the original two 15-minute strategies. There is no historical/out-of-sample validation of the new suite yet; the unit tests validate implementation, not returns.

Validation: payoff endpoints, futures ledger, shared limits, overlap, calendar validation/expiry, complete-bar warm-up, daily-IV recording, stale/mismatched/all-or-none execution, loss-trigger exits, preserved migrations and subscriptions. Run `PYTHONPATH=. python -m pytest options_lab/tests tests/test_route_offload.py -q` inside `intelligence-engine` and the normal frontend build.
