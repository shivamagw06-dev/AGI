# Live Alpha session recovery — 5 October 2026

All five engines retain their scoring rules and research-only execution policy.

- Recover actual current-session Upstox one-minute OHLC and supplied futures OI after startup, and once each new session. Two workers, 250 ms pacing, 15 s request timeout, at most three recovery passes per session. Authentication and throttling stop a pass. Recovery progress is exposed in `bootstrap.intraday`.
- Opening ranges require observations in all 15 opening minutes (09:15–09:29 IST). Recover these even when older than the rolling two-hour feature retention. Candles must be completed and belong to the current session.
- Removed previous-close values falsely timestamped as 15/60-minute observations. Missing data remains missing; null returns no longer become zero through Number(null). Lookback anchors must be within two minutes of their requested timestamp.
- Historical candle close times are preserved. No historical signals or live ticks are fabricated. Bootstrap data is used in memory; the provider is queried again after restart rather than relabelling historical candles as received live snapshots.
- Distinguish mapped futures awaiting usable OI history from absent futures mappings. Overall evaluation status remains degraded while any engine is unavailable, including between five-minute evaluations.
- Old published signals are not rewritten. Earlier outputs that used previous-close seeds should not be treated as validated intraday evidence.

Validation: 97 focused Live Alpha/feed tests passed, including genuine-history evaluation of all five engines, missing opening minutes, stale/gapped history, incomplete candles, OI recovery, and rate-limit stop behavior. Read-only production samples confirmed current-session NIFTY and Reliance minute candles back to 09:15 IST.
