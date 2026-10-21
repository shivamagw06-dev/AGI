# Live Alpha integrity audit — 8 October 2026

Observed production snapshot: five engines last persisted 6 October at 09:55 UTC. Groww fallback produced no usable snapshots, with repeated budget deferrals obscured as decode errors. Newer price overlays do not refresh historical classifications.

An indicative comparison of the stale snapshot's 15 +99 stocks found ten lower and five higher, mean price change -1.61%; timestamps differ, so this is not a controlled backtest. Negative classifications were not universally inverted. Momentum ranks relative residual strength and may flag a stock that falls less than peers. Shared price/volume inputs make engine agreement correlated.

Repairs: withhold stale snapshots from current signal lists; average component scores instead of dividing their sum by square root of count; record the new score model in publication quality metadata; pace Groww one quote per second, abort a poll on authentication/quota refusal, and separate request failures from malformed quotes; expire empty minute-candle caches after one minute and propagate authentication failures instead of caching them as missing instruments.

Recent due evidence sample: 2,852 nifty_no_candles, 2,131 stock_no_candles, 17 stock_before_first_candle. Missing observations are not losses. Evidence now exposes reasons and a separately labelled completed-only sample, avoiding concealment of older completed measurements behind recent misses. Existing stored publications, missed records and strategy thresholds are unchanged. This does not recover missing market history or demonstrate predictive edge.

Validation must follow recovery: fresh source timestamps and evaluations, fixed entry/exit horizons, per-engine and direction outcomes, market-adjusted results, non-overlapping samples, costs, and held-out sessions. Do not optimise thresholds to the observed losing sample or reverse signals based on it. Single-instrument polling across 500 names remains a fallback with limited simultaneous coverage; a connected streaming source is needed for broad timely intraday evaluation.

Latest 5,000 completed observations within 30 days, one-hour horizon: Leadership n=983, mean -0.144%, positive 40.8%; Activity n=750, -0.088%, 44.1%; Breakout n=1,147, -0.007%, 50.0%; Mean Reversion n=241, +0.088%, 58.5%; Positioning n=11, -0.206%, 45.5%. Values subtract stored costs, which may be zero. This completed-only, overlapping sample excludes missing outcomes and is not a tradable portfolio backtest or unbiased population estimate.
