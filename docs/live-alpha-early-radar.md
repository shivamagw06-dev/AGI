# Live Alpha early setup radar

Version: early-range-v1. Research only; no broker orders. No claim of prediction before public market evidence or improved profitability.

## Design

The new default Setup radar tab is separate from the existing five-engine ranking and its published signal archive. A 30-second per-stock scan reuses streamed quotes and the in-memory minute feature store. No additional broker requests. A five-second timer checks the scan bucket; overlapping scans are prevented. Stream ingestion updates features independently of the persistence queue. The browser checks the small radar endpoint every 15 seconds while visible. Existing broad cross-sectional rankings retain their coverage gate and five-minute cadence.

## Fixed experimental rules

All inputs must be observable at evaluation. Fifteen preceding complete minute buckets, same-day benchmark history, a quote no older than 30 seconds, and valid bid/ask within 0.2% are required. Levels are the high/low of preceding minute samples, not exact candle high/lows. Range width must be 0.1–1.5%. Volume pace is the recent actual cumulative-volume change per minute divided by pace across the preceding observed period. Missing/reset volume blocks the setup; historical OHLC is not fabricated into volume.

- Watch: signed distance to relevant boundary −0.2% to less than +0.08%; participation at least 1.2×; absolute benchmark-relative move at least 0.1 percentage points.
- Trigger: at least +0.08% beyond frozen boundary; participation at least 1.5×; absolute relative move at least 0.2 points.
- Extended: more than 0.6% beyond boundary. No trigger or implied entry recorded.
- Follow-through: at least one minute after trigger and at least +0.15% directional price movement.
- Failure: at least 0.15% back through the frozen boundary. Original trigger retained.
- Watch expiry: ten minutes. Trigger observation: one hour, then expiry. Terminal episodes have a 15-minute cooldown.

Direct triggers without a preceding watch are permitted and never backdated. The original trigger time and price are immutable. Stage transitions preserve the sampled price at the transition. Returns are directional price changes before costs, not fills or trade returns. Failed, extended and expired states remain visible.

## Storage and rollout limitations

Stage transitions append to `live_alpha_radar_events`; the latest episode state is upserted separately into `live_alpha_radar_state`. Idempotent event keys permit retries after partial writes. Restoration loads the current session state; failed recovery prevents new radar evaluations until recovery succeeds. No anonymous or authenticated direct table access; RLS enabled, writes server-only. The UI shows the latest 100 transitions; the journal retains older transitions without application deletion. Pending writes remain in the bounded 20,000-event memory window and are explicitly flagged if storage fails. Existing database publication history is unchanged.

This is not yet a validated performance engine: 5/15/30/60-minute bid/ask outcomes and cost-adjusted chronological comparisons remain necessary. No historical backtest has been run for these new rules.

Legacy ±99 scores remain solely in the old ranking and archive for comparability. The new radar uses stages and observable reasons instead of an uncalibrated confidence number.

## Validation

Automated checks cover current/future-point exclusion, missing-minute coverage, stale quotes, depth, cumulative-volume resets, watch→trigger→failure, frozen levels and prices, extended moves, restart restoration, journal failures, session gating and scan deduplication. Existing Live Alpha regression suites must pass. Production build must pass. This is software correctness evidence, not trading-performance evidence.

Before activating for clients: verify actual quote/depth coverage and resource use in an open session; verify journal writes; replay genuine point-in-time observations across multiple days with baseline and doubled costs; compare time-to-detection, false triggers, adverse excursion and subsequent returns against the unchanged legacy engine on held-out days. Do not tune to IGL alone.
