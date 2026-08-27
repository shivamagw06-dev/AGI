# Continuous Historical Backfill Until Coverage Stabilises

The historical backfill engine **keeps draining a persistent company queue** until hard requirements are met for every currently listed company, then switches to **maintenance-only**. Coverage is **never permanently finished** — the listed universe changes over time.

## Living universe

Mission Control tracks:

| Metric | Meaning |
|--------|---------|
| Current Listed Universe | Active supported listings |
| Covered Companies | Hard-complete / maintenance |
| Coverage % | Covered ÷ listed |
| New Listings | Diff vs prior snapshot (auto-enqueued) |
| Delisted Companies | Removed from active listed set |
| Pending IPOs | Registered pre-listing names |

### IPO path

```text
IPO detected / registered
→ Automatically create/enqueue company
→ Historical backfill from listing date
→ Hard-complete → maintenance mode
```

The queue may be **empty of pending work**, but it is **always ready** to accept new listings without manual intervention.

## Hard vs soft completion

| Hard (gates maintenance) | Soft (richness only) |
|--------------------------|----------------------|
| OHLCV | Investor presentations |
| Corporate actions | Earnings transcripts |
| Financial statements | IR PDFs |
| Shareholding | Historical news |
| Embeddings | ESG reports |
| QA | |

Soft gaps (e.g. no 2011 transcripts) **do not** permanently mark a company incomplete.

Mission Control scorecard example:

```text
RELIANCE   Hard 100%   Soft 83%   Overall 96%
```

## Knowledge density

Per company:

`Years · Documents · Extracts · Embeddings · Density (Excellent / Good / Moderate / Thin)`

Density measures how rich the intelligence is — not only whether the name was processed.

## Modes

| Mode | When | Behaviour |
|------|------|-----------|
| `deep_backfill` | pending hard backlog > 0 | Prioritised batches; faster CGL interval |
| `maintenance` | hard backlog = 0 | Incremental refresh; queue stays ready for IPOs |

## Flags

| Flag | Default | Meaning |
|------|---------|---------|
| `CONTINUOUS_HISTORICAL_BACKFILL` | true | Master backfill switch |
| `CONTINUOUS_BACKFILL_UNTIL_COMPLETE` | true | Drain until hard backlog empty |
| `CONTINUOUS_BACKFILL_ACTIVE_INTERVAL_SEC` | 300 | Faster interval while backlog remains |
| `KF_HD_BACKFILL_BATCH` | 12 | Companies per batch |
| `KF_HD_BACKFILL_BATCHES_PER_CYCLE` | 3 | Batches per CGL wake |
| `KF_HD_TARGET_YEARS` | 15 | Depth target |
| `KF_HD_LIVE_COLLECTORS` | true (Render) | Yahoo live OHLCV |

## Operational verification (days/weeks)

Watch Mission Control for:

1. Backlog steadily shrinking  
2. Coverage % rising  
3. Average historical depth increasing  
4. Knowledge extracts + embeddings growing  
5. Collector error rates staying low  
6. Newly listed companies appearing on the queue automatically  
