# AGIB — Always-On (No Cold Starts)

## What actually causes a cold start / raw 502

| Cause | Fix |
|---|---|
| **Render `plan: free`** — free web services sleep after ~15 min of no traffic; next request pays a 30–60s cold-start penalty (sometimes a raw Render 502 while spinning up) | Use a **paid plan (Starter or higher)** — paid services never sleep on inactivity |
| **Deploy-triggered restart** — every merge to `main` touching `server/**` or `intelligence-engine/**` auto-redeploys via `.github/workflows/deploy-render.yml`; the old instance is replaced while the new one boots | Health-check-gated rolling deploy (already configured via `healthCheckPath`) minimizes the gap; back-to-back merges within minutes can still overlap and extend it |
| **No external keep-warm signal** | `.github/workflows/keep-warm.yml` pings both services every 10 minutes |

## Fix #1 — Paid plan on both services (the real fix)

`render.yaml` now declares `plan: pro` for **both** `agib-api` and `agib-intelligence-engine`, matching the account's actual Render plan (4 GB / 2 CPU each).

**Important — keep this value in sync with the dashboard.** Render's Blueprint docs are explicit: *"In your Blueprint file, set your service's plan field to a new instance type... the next time you sync your Blueprint, Render triggers a new deploy to apply the new instance type."* That means if `render.yaml` ever specifies a **lower** plan than what's actually configured in the dashboard, a Blueprint re-sync can silently **downgrade** the live service to match the file — the opposite of what we want.

Confirm in the Render dashboard that both show **Pro**:

1. `agib-api` → Settings → Instance Type → **Pro**
2. `agib-intelligence-engine` → Settings → Instance Type → **Pro**

Free plan should only ever be used for scratch/preview services, never for the two production services users depend on.

## Fix #2 — Keep-warm ping

`.github/workflows/keep-warm.yml` runs every 10 minutes, hitting:

- `GET https://finance-news-backend-19i5.onrender.com/api/health`
- `GET https://agib-intelligence-engine.onrender.com/v1/health`

This is a second layer of defense (useful even on paid plans, e.g. after long idle low-traffic windows) and doubles as an uptime signal — a failing ping shows up as a workflow warning in the Actions tab.

## Fix #3 — Deploy-triggered restarts are still expected, minimized not eliminated

Both services already declare `healthCheckPath` (`/api/health`, `/v1/health`), which lets Render wait for the **new** instance to pass health checks before routing traffic to it — this is what makes paid-plan deploys close to zero-downtime.

What it does **not** eliminate:

- Multiple merges within a few minutes can trigger overlapping deploys, extending the window without a fully-warm new instance.
- A slow-booting engine (heavy Python imports) can take longer to pass its first health check than the deploy hook expects.

If frequent 502s during active development sessions matter, consider batching merges (squash multiple PRs before triggering a deploy) rather than pushing every PR to `main` individually during a burst of work.

## Verify

```bash
curl -sS https://finance-news-backend-19i5.onrender.com/api/health
curl -sS https://agib-intelligence-engine.onrender.com/v1/health
```

Both should return `200` with JSON in well under a second once the plan change is applied and the keep-warm workflow has run at least once.

## Gather vs Mission Control

If `/v1/health` is fine but Mission Control times out while FSE/CGL logs flood, gather is starving the HTTP process. Use the **gather sidecar** (default) or optional dedicated worker — see [`AGI_GATHER_WORKER.md`](./AGI_GATHER_WORKER.md). Do **not** solve this by only upgrading the web plan.
