# Live Intelligence Activation

**Goal:** Ship the AGIB research-terminal website with the full intelligence stack reachable in production.

## Production surfaces

| Surface | URL |
| --- | --- |
| Website | https://agarwalglobalinvestments.com |
| Ask AGI | https://agarwalglobalinvestments.com/ask |
| Mission Control | https://agarwalglobalinvestments.com/admin/mission-control |
| Node API | https://finance-news-backend-19i5.onrender.com |
| Intelligence engine | https://agib-intelligence-engine.onrender.com |

## What this activation does

1. Rebuilds Hostinger root (`index.html` + `assets/`) with research-terminal homepage + intelligence UI
2. Adds Node proxies for IIEX, MKFI, and `/api/intelligence/live-status`
3. Serves a **Node Ask desk fallback** when the Python engine is cold/OOM (so Ask stays usable)
4. Turns off FAA background collector by default on Starter (reduces OOM loops)
5. Soft-surfaces live stack health on the homepage

## Required GitHub secrets (Hostinger workflow)

```text
VITE_API_URL=https://finance-news-backend-19i5.onrender.com
VITE_SUPABASE_URL=https://zrvdtpxfmuijhionbaxr.supabase.co
VITE_SUPABASE_ANON_KEY=<full anon JWT>
FTP_SERVER / FTP_USERNAME / FTP_PASSWORD
```

Optional but recommended:

```text
RENDER_DEPLOY_HOOK_API=<Render deploy hook for agib-api>
RENDER_DEPLOY_HOOK_ENGINE=<Render deploy hook for agib-intelligence-engine>
```

## Verify after merge to main

```bash
curl -sS https://agarwalglobalinvestments.com/ | rg -o 'assets/index-[^"]+\.js'
curl -sS https://finance-news-backend-19i5.onrender.com/api/health
curl -sS https://finance-news-backend-19i5.onrender.com/api/intelligence/live-status
curl -sS https://agib-intelligence-engine.onrender.com/v1/health
curl -sS https://agib-intelligence-engine.onrender.com/v1/system/intelligence-stack
```

Ask smoke:

```bash
curl -sS -X POST https://finance-news-backend-19i5.onrender.com/api/ui/search \
  -H 'content-type: application/json' \
  -d '{"question":"What is the Nifty outlook?"}'
```

Expect either a full engine SearchView **or** `mode: "node_desk_fallback"` (200) while the engine warms.

## Ops notes

- Homepage works even when the engine is restarting (`/api/ui/home` Node enrichment).
- Full Ask depth returns after the engine recovers (`ASK_SLIM=true` on Starter).
- Set `ASK_SLIM=0` / re-enable `FAA_BACKGROUND_COLLECTOR` only after Render memory headroom is proven.
