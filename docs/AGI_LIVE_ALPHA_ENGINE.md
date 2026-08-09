# AGI Live Alpha Engine

## Objective

Turn synchronized Upstox observations into research candidates, then measure whether those candidates produce return beyond benchmark, costs and slippage. The engine is research-only. It cannot create orders, positions, quantities or targets.

The product label remains **Live Alpha Signals** until a factor demonstrates statistically meaningful, out-of-sample excess return after costs. Only then may that specific factor be labelled **AGI Validated Alpha**.

## Build sequence

1. Cross-sectional residual momentum — implemented in Phase 1.
2. Volume and liquidity anomaly.
3. Opening-range expansion.
4. Intraday mean reversion with shock/regime filter.
5. Derivatives positioning and open-interest classification.
6. Regime-aware composite after out-of-sample validation.

## Data flow

`Upstox V3 feed -> decoder -> synchronized snapshot -> factor engine -> private signal store -> research UI`

The V3 stream is binary Protobuf. The collector must obtain the authorized WebSocket URL, follow its redirect, subscribe using V3 binary messages and decode the official Market Data V3 schema. Full mode provides LTPC, market depth, intraday/day OHLC, average traded price, cumulative volume and OI. Historical and intraday candle APIs provide calibration and replay baselines.

## Phase 1 contract

One simultaneous stock snapshot contains 15- and 60-minute stock, benchmark and sector returns, cumulative volume, expected cumulative volume, spread and liquidity state. The engine calculates:

`residual return = stock return - benchmark return - sector return`

`score = 30% z(residual 15m) + 30% z(residual 60m) + 20% z(volume surprise) + 20% z(sector strength)`

The weights are configuration, not a permanent claim. They must be learned and validated through walk-forward testing before any output is called alpha.

The live `signal_quality` score measures current factor strength and data quality. It is explicitly non-empirical. `empirical_confidence` remains unvalidated with a null score until sufficient comparable historical outcomes exist.

## Empirical validation

Every signal is evaluated independently at 5 minutes, 15 minutes, 30 minutes, 1 hour, close, next day and 5 days. The validator records sample size, hit rate, average and median net alpha, winner/loser behaviour, expected value, information coefficient, signal Sharpe, maximum drawdown, turnover, estimated costs and cumulative net alpha. Results are also sliced by market regime.

## Production gates

- At least 10 synchronized instruments; production target is the liquid NSE universe.
- One timestamp boundary across the cross-section.
- Minute-of-day volume baselines built only from prior sessions.
- Spread and minimum-liquidity filtering before candidate publication.
- Raw observations retained separately from derived factors.
- No look-ahead data in replay or backtest.
- Report benchmark-relative return after fees and slippage.
- Promote weights only after out-of-sample and regime-sliced validation.

## Next implementation

The forward-outcome lifecycle is now defined. Every persisted directional signal schedules measurements at 5m, 15m, 30m, 1h, close, next day and 5d. Each completed observation records raw return, beta-adjusted market alpha, sector-relative alpha, estimated costs and net alpha. Missing prices remain pending for a bounded retry rather than being silently converted to zero.

The Upstox V3 collector and synchronized snapshot clock are now implemented. The collector requests the one-time authorized WebSocket URL, subscribes in binary Full mode, decodes the official Protobuf contract, normalizes price/volume/depth/OI observations, rejects stale or high-skew cross-sections and reconnects with bounded exponential backoff. The feed remains opt-in until its production universe and persistence adapter are configured.

Normalized batches can now be downsampled into the private snapshot store, and point-in-time-safe median cumulative-volume curves can be built from prior sessions. The opt-in shadow pipeline keeps two hours of rolling features, requires complete 15- and 60-minute stock/sector/Nifty history plus a valid volume baseline, and evaluates Momentum Strategy #1 once per five-minute bucket. It remains research-only and skips incomplete universes rather than filling missing observations.

The runtime now validates an explicit liquid-NSE universe, deduplicates all stock/sector/benchmark subscriptions, wires the collector to persistence and the Momentum shadow pipeline, schedules forward outcomes for directional research candidates, and exposes `/api/market/live-alpha/status`. Startup remains disabled unless `LIVE_ALPHA_SHADOW_ENABLED=true`.

Strategy #2, volume/liquidity anomaly, now runs from the same synchronized snapshots and point-in-time-safe volume baselines. It flags only abnormal participation above 1.25x expected cumulative volume, applies the same spread/liquidity gate, labels accumulation versus distribution from residual price direction, persists its research signals and schedules the same forward outcomes.

Strategy #3, opening-range expansion, records the first 15 minutes of each session and evaluates later expansion beyond that range. Candidates require a 0.10% breakout buffer, at least 1.10x expected cumulative volume, acceptable spread, and an opening range between 0.15% and 3%. Missing opening observations fail closed, preventing a mid-session restart from inventing a range.

Strategy #4, intraday mean reversion, ranks extreme 15-minute stock-versus-sector residual shocks and researches the opposite-direction response. It rejects broad-market moves above 0.75%, volume above 2.5x baseline, wide spreads, and moves dominated by an established 60-minute trend. These gates are designed to avoid mechanically fading market stress, persistent information, or illiquid prints.

Next, apply all migrations, populate at least five prior sessions of minute volume baselines, verify every configured index key with Upstox, and run a controlled market-hours soak test. The acceptance gates are stable connectivity, fresh synchronized coverage, low decode errors, complete baseline coverage and consistent five-minute shadow runs for both implemented engines.
