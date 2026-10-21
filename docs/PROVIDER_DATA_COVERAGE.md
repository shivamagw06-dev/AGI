# Nifty provider coverage audit

The private paper-agent desk contains an authenticated provider coverage panel.
Open it and run the read-only audit. POST starts one bounded background job;
GET reads progress. Concurrent runs are coalesced, and completed runs have a
five-minute cooldown. No account data or order endpoints are accessed.

## What a test establishes

Passed means a nonempty sample met that probe's schema checks. It does not mean
complete historical coverage, continuously healthy streaming, or a profitable
strategy. Empty is distinct from failure. Failed messages use fixed error codes
rather than provider response bodies. No token values reach the browser.

Probes cover Nifty spot, one-minute history, expiry/contract discovery, an expired
call and future sample, current option chains and an Upstox news sample. Quote
checks after close do not establish live freshness. Historical strike selection
is a capability sample, not a trading decision or point-in-time backtest.

Streaming sessions, full constituent coverage, event review, basket margins and
long-term retention remain explicitly untested until their dedicated evidence is
available. Existing Upstox strategy integration is labelled separately from these
REST probe results. A working REST endpoint must not automatically turn on trading
or failover.

## Storage

Set PROVIDER_COVERAGE_DIR to a directory on an existing persistent disk to retain
reports and sample files through deployment. Without it, files use a temporary
directory, clearly labelled in the UI. Files are owner-only, raw samples are not
served through the API, and each audit replaces its bounded samples. This is not
the long-term tick recorder. A deployment interruption leaves an unfinished report
labelled interrupted; a fresh audit can be started.

## Groww history migration

/historical/candles replaces the deprecated /historical/candle/range. CASH symbols
map to EXCHANGE-SYMBOL. FNO callers must pass a discovered canonical groww_symbol;
we do not guess derivative encodings. Requests are split into the documented
30/90/180-day windows depending on interval, for a maximum total of two years.
Boundaries are deduplicated and returned in ascending time order. Naive provider
timestamps are interpreted as IST, with legacy numeric epoch seconds preserved
for existing consumers. Requests have a 15-second deadline and reject redirects.

## Next integration gates

1. Pass real account probes and examine coverage before backfilling a full year.
2. Observe Groww streaming in a separate process, without changing Upstox fills.
3. Compare contract identifiers, exchange timestamps, quote ages and both-leg depth.
4. Validate complete same-provider baskets before introducing any failover.
5. Separately verify durable tick retention and storage budget for 6–12 months.
6. Run out-of-sample comparison before allowing coordinator decisions to affect entries.
