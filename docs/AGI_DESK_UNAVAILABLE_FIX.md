# AGI Desk “Temporarily unavailable” fix

## Symptom

Ask AGI Desk showed:

> Temporarily unavailable — The research desk could not complete this briefing.

## Cause

Live `POST /api/ui/search` often returned Render **HTML 502** after ~45–60s when the intelligence engine blocked, restarted, or OOMed under Ask load.

Contributing factors:

1. `/v1/ui/search` called sync `UiService.search` on the asyncio event loop (health checks starved).
2. Investment Office soft-wire could raise or grow in-memory stores if persist stayed on.
3. Node gateway forwarded raw HTML 502 to the browser instead of a retryable JSON error.

## Fix

- Run `UiService.search` via `run_in_threadpool`; map unexpected failures to JSON 503.
- Wrap AGI v4 offices in best-effort try/except; default `AGI_V4_OFFICE_PERSIST=0`.
- Gateway: on HTML/502/503, wake `/v1/health` once and return `{error: research_desk_unavailable, retryable: true}`.
- Client: one automatic retry after ~2.5s on retryable desk errors.

## Env (Render engine)

| Key | Default | Meaning |
|-----|---------|---------|
| `AGI_V4_OFFICES_IN_ASK` | `1` | Soft-wire offices into Ask; set `0` to skip |
| `AGI_V4_OFFICE_PERSIST` | `0` | Do not persist office objects on Ask path |
| `AIL_LIVE_FAA` | `0` | When off, Ask/AIL skips unbound `faa.acquire` (Playwright hang) |

## Follow-up root cause (architecture)

Even with JSON 503 + retries, Ask timed out because collectors sat on the request path. Sprint A removes `faa.acquire` from Ask entirely and moves FAA to a background collector — see `docs/AGI_ASK_NO_FAA_ARCHITECTURE.md`.
