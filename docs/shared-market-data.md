# Coordinated market data

Live Alpha keeps Upstox full-mode streaming as its primary real-time source. Groww is used concurrently by daily research/ticker services and for half of eligible Live Alpha cash-history recovery requests, partitioned deterministically by ISIN. Failed history requests may fall back to the other provider. Index and futures history retain Upstox canonical identifiers. Groww cash mapping requires an unambiguous matching NSE ISIN in its daily instrument master; unknown instruments are not guessed. Each returned history comes from one provider, never a splice. Rules, publication prices, positions and event reviews are unchanged.

## Node API budget

`marketDataBudget` reserves requests before sending them. Its conservative process allocation is Upstox 4/second, 120/minute, 800/30 minutes and Groww 2/second, 100/minute. These values deliberately leave capacity for the separate Python engine and other tools. They are NOT an account-wide distributed rate limiter. Other processes, external clients and restarts cannot be accounted for by this in-memory budget; do not claim exhaustion is impossible or scale replicas without revisiting these allocations.

The primary provider modules, India portfolio live/daily prices, NSE screener quotes, FX indicators and coverage probes use this budget. WebSocket messages are not HTTP requests and do not pass through it. Broker writes are not supported by the wrapper. HTTP 429 honors Retry-After with at least a 60-second cooldown; 401/403 also pause requests for a minute. Requests whose reservation would require over 20 seconds fail explicitly for retry on the next scheduled cycle. No unbounded queue, background retry storm or stale-success substitution. Network calls have a timeout.

Identical simultaneous GETs coalesce, partitioned by a one-way credential hash. Successful quote responses can be reused for two seconds; historical responses are not retained. Provider timestamps remain unchanged. No credentials or request URLs appear in status metrics.

India portfolio prices reuse Live Alpha trade observations only if no older than 30 seconds. Missing instruments are requested in batches of at most 500. Signal-time anchors and portfolio baselines are not rewritten. Groww fallback publishes each small polling batch immediately rather than holding the earliest quotes until a complete scan finishes. Polling pauses outside NSE sessions and resumes on the next scheduled cycle. Groww polling is not equivalent to tick streaming and remains subject to all freshness/warm-up rules.

## Verification

`/api/market/live-alpha/status` includes `data_budget`, `shared_quotes` and `history_routing`. These counters are since Node startup. The active stream is still reported separately in `provider_policy`. Both providers being configured is not proof of successful requests: verify nonzero successful provider history counters when recovery runs in an open session. Review deferred calls/cooldowns, warm-up coverage and actual exchange timestamps. Token expiry and provider outages can still interrupt coverage. No paid capacity or services were added.

Tests cover concurrent budget enforcement, independent provider allocations, deduplication, 429 cooldown, credential isolation, read-only enforcement, stale/future quote rejection, portfolio quote reuse, exact history mapping/fallback, malformed history and Groww polling lifecycle.

Recovery retries use a 30-minute rest after three failed attempts and then resume during the session, rather than permanently giving up for that date. This does not override an expired credential or fabricate missing history. Public Groww master audit on 5 October 2026 matched all 500 Nifty 500 ISINs unambiguously.

Background requests have lower sub-budgets (Upstox 2/second, 80/minute, 550/30 minutes; Groww 1/second, 60/minute) within the overall allocations. This reserves HTTP capacity for current quotes. At most 96 background requests may be pending within a total 128-request cap. WebSocket processing remains independent of either queue.
