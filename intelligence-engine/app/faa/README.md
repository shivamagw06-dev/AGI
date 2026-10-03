# FAA — Finance Acquisition Agent v1.1

Production-grade **live acquisition** layer for AGIB.

```text
FAA (Acquire) → FRE (Retrieve & Rank) → CAE → Ask AGI
```

FAA never answers and never reasons.

## Services

| Service | Responsibility |
|---------|----------------|
| Discovery | Multi-task plans + connector routing |
| Fetch | Parallel HTTP/PDF/RSS/XLSX/JSON + retries/backoff/rate-limits |
| Processing | Clean + metadata extraction |
| Index | Immutable versions + automatic FRE ingest |

## Connectors

Company IR · NSE · BSE · SEBI · RBI · MCA · PIB · Government · News · RSS · Tavily · Exa · SerpAPI · Google CSE · Bing · Generic HTML · Generic PDF

Each connector exposes: `search()`, `fetch()`, `validate()`, `health()`, `priority()`, `supported_document_types()`.

## Live fetch

```text
FAA_LIVE_FETCH=true
FAA_MAX_WORKERS=6
TAVILY_API_KEY=...   # optional
```

## Cache / versions

Skip download when URL / ETag / Last-Modified / SHA256 unchanged.  
Never overwrite — create immutable versions with `superseded_by`.

## Scheduler cadences

| Stream | Cadence |
|--------|---------|
| Exchange filings | every 5 minutes |
| News | every 5 minutes |
| RSS | every 10 minutes |
| Government | hourly |
| Annual reports / presentations | daily |
| Quarterly reports | hourly in earnings season |

## Observability

Health exposes connector status, queue depth, worker count, cache size, live-fetch flag, last successful acquisition, fetch/parse/embed latency, rate-limit events.

## APIs

`/v1/faa/health|dashboard|discover|acquire|connectors|jobs|consult|scheduler`

## Background collection policy

FAA does not acquire documents on the Ask request path. The default scheduled
policy uses `Asia/Kolkata` time:

- 01:00 IST: bounded daily research collection, with a 60-minute start window
  and maximum runtime budget of 3,600 seconds.
- 18:00 IST: small post-market filings and regulatory sweep, capped at 900
  seconds.

The collector runs each window at most once per local date. It stops starting
new queries when the runtime deadline is reached and reports remaining work as
deferred. Intraday market prices remain owned by market-data providers, while
Ask AGI's bounded external search remains independent.

Configuration: `FAA_NIGHTLY_HOUR_IST`, `FAA_NIGHTLY_MAX_RUNTIME_SEC`,
`FAA_NIGHTLY_LIMIT`, `FAA_EVENING_FILINGS_SWEEP`, `FAA_EVENING_HOUR_IST`,
`FAA_EVENING_MAX_RUNTIME_SEC`, and `FAA_EVENING_LIMIT`.

BFF: `/api/intelligence/faa/*`
