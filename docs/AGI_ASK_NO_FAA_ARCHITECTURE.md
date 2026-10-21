# Ask AGI — collectors off the request path (Sprint A)

## Rule

**Never let a browser (Playwright / FAA acquire) decide whether the user gets a response.**

```text
Users → Intelligence Engine → reads index / snapshot store
                                      ▲
                                      │
                         FAA background collector
                         (Yahoo / News / filings / Playwright)
```

## Sprint A changes

1. **Remove `faa.acquire` from Ask**
   - `FreService.consult` always uses `acquire=False` (seed/index only)
   - `AilPipeline.soft_pull_upstream` reads FAA **snapshots** + FRE **search/consult** only
   - `AilService.package_for_ask_agi` never passes live acquire

2. **FAA is a background collector**
   - `app/faa/background.py` daemon thread started in engine lifespan
   - Calls `FaaService.refresh_snapshots()` on an interval
   - Env: `FAA_BACKGROUND_COLLECTOR`, `FAA_COLLECTOR_INTERVAL_SEC`, `FAA_COLLECTOR_LIMIT`

3. **Hard timeouts on Ask external soft-deps**
   - `app/ui/timeouts.py` → `call_with_timeout`
   - LEO ≤5s, FRE consult ≤3s, AIL ≤4s (override via `ASK_EXT_TIMEOUT_SEC`)

4. **Graceful degradation**
   - `SearchView.status` = `ok` | `degraded`
   - `SearchView.degradation` records which layers timed out / used cache
   - Briefing still returns when optional collectors are unavailable

## Explicit live acquire (allowed)

| Path | Purpose |
|------|---------|
| `POST /v1/faa/acquire` | Manual / ops crawl |
| `POST /v1/faa/jobs` | Full watchlist batch |
| Background collector | Periodic snapshot refresh |

## Not in Sprint A (later)

- Parallel `asyncio.gather` for Yahoo/news/SEC
- Persistent Postgres snapshot tables for FAA
- Redis queue + dedicated FAA worker process
- Playwright browser reuse / semaphore (Phase 6–7)
