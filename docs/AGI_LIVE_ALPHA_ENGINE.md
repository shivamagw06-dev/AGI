# AGI Live Alpha Engine

## Objective

Turn synchronized Upstox observations into research candidates, then measure whether those candidates produce return beyond benchmark, costs and slippage. The engine is research-only. It cannot create orders, positions, quantities or targets.

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

Build the Upstox V3 Protobuf collector and snapshot clock. It should use one full-mode stream for the selected liquid universe, reconnect with bounded backoff, detect stale instruments and write minute bars/raw feed health. Strategy #2 then reuses those minute-of-day volume baselines.
