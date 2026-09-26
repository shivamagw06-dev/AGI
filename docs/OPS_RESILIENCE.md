# AGI Operational Resilience

Hardening for production deploy races, market quote degradation, and automated FII/DII ingest.

## 1. Asset versioning (Hostinger)

Every Hostinger build writes:

* `public/version.json` → deployed as `/version.json`
* `.build-id` → injected as `import.meta.env.VITE_BUILD_ID`

Client (`src/lib/buildVersion.js`):

* Polls `/version.json` every 60s
* On mismatch with the bundled build id → **one** automatic reload
* ErrorBoundary also reloads once on Vite chunk / CSS preload failures

`.htaccess`:

* `index.html` + `/version.json` → `no-cache, no-store`
* `/assets/*` → `max-age=604800, immutable`

## 2. Index / quote graceful degradation

```
Live Quote → in-memory cache → last successful snapshot → UI (never empty)
```

* `/api/indices` serves last-good for 30 minutes on NSE failure / empty payload
* Home market snapshot returns last successful prints with `liveUnavailable: true`
* Market strip shows **Snapshot** + “Live unavailable · Updated HH:MM” instead of blank loading

## 3. FII/DII daily automation

Scheduler: `server/services/institutionalFlowScheduler.js`

```
18:05 IST (weekdays)
  → Upstox FII/DII
  → Market Intelligence ingest
  → warehouse.institutional_flow
```

* Manual fallback: `POST /api/market/upstox-flows/refresh`
* Status: `GET /api/market/upstox-flows/status`
* Disable: `INSTITUTIONAL_FLOW_SCHEDULER=false`

## 4. Mission Control probes

Added source-health cards:

* Groww
* Upstox FII/DII
* Market Indices
* Scheduler note includes FII/DII EOD
