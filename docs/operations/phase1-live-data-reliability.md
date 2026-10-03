# Phase 1: Live Data Reliability

**Started:** 14 August 2026  
**Scope:** Existing Upstox/Groww live collection only; no historical backfill.

## Provider Contract

| Role | Provider | Rule |
|---|---|---|
| Primary Live Alpha feed | Upstox V3 WebSocket | Full Nifty 200 equity, index and available futures subscriptions |
| Research fallback | Groww quote polling | Activates only when Upstox fails/auth-fails and fallback is explicitly enabled |
| Groww research schedulers | Groww | Sector rotation and equity opportunity; separate from the five-model composite |
| Historical fundamentals | AGI warehouse | Existing inventory; continuous backfill disabled |

Provider fallback never enables execution. All outputs remain research-only.

## Canonical Timestamp Contract

Every accepted live snapshot records:

- `exchange_timestamp` when supplied by the provider;
- `provider_timestamp` when supplied by the feed server;
- `ingested_at` when AGI received the observation;
- `effective_timestamp`, chosen exchange-first, then provider-server, then ingestion;
- `timestamp_source`, identifying that choice.

The snapshot store rejects invalid timestamps, future-dated exchange observations and
out-of-order ticks. Freshness and synchronization use `effective_timestamp`, not merely
the time AGI happened to receive a message. Rejection counters are exposed in Live
Alpha feed health and the UI.

## Signal Gate

A live quote is blocked when the feed is disconnected, the instrument is unmapped, no
quote has arrived, the effective timestamp is invalid, or the quote is stale. Strategy
Lab retains its completed-session signal price separately and may only display a live
price as an independently labelled validation field.

## Baseline Evidence

At 14 August 2026 10:59 UTC (16:29 IST, after the NSE continuous session):

- Upstox V3 feed authorization passed and the WebSocket was connected.
- Upstox corporate-actions health passed using the configured access token.
- Groww passed quote, batch LTP and OHLC probes (3/3).
- Live Alpha subscribed to 395 instruments for the complete Nifty 200 universe.
- 184 futures mappings were resolved; 16 members had no mapped future.
- Volume baselines reported 75,000 rows covering all 200 equity instruments.
- The evaluation remained in warm-up because a complete simultaneous universe was not
  available after market close; this is not recorded as a successful strategy run.
- Hedge Fund live-quote and candle schedulers were enabled but correctly idle after
  market close.

## Remaining Acceptance

Phase 1 is accepted after one open-market observation confirms:

1. Upstox messages advance continuously with no unexpected timestamp rejections.
2. All required equity/benchmark/sector inputs meet freshness and skew gates.
3. Each eligible Live Alpha strategy persists a non-orphaned run or an explicit,
   evidence-backed exclusion reason.
4. A controlled provider-failure test proves Groww fallback and recovery to Upstox.
