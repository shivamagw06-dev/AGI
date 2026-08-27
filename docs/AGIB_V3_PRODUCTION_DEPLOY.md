# AGIB v3 Production Deploy

## What goes live

Full frozen institutional architecture on website + Render:

```text
FIL → FDI → MII → ACI → EIL → PIL → CIG → IKG → FIE → ILM → SSL
→ Analysts → IC → PIO → IDE V2 → CIO → Research Writer → ACS → IRS
```

## Surfaces

| Surface | URL |
|---|---|
| Website | https://agarwalglobalinvestments.com |
| Ask AGI | https://agarwalglobalinvestments.com/ask-agi |
| Admin Decision Engine V2 | `/admin/decision-engine-v2` |
| Admin Simulation Lab | `/admin/simulation-lab` |
| Admin Learning & Memory | `/admin/institutional-memory` |
| Node API | https://finance-news-backend-19i5.onrender.com |
| Intelligence Engine | Render service `agib-intelligence-engine` |

## Deploy path

1. Merge this PR into `main`
2. GitHub Actions:
   - **Deploy to Hostinger** rebuilds/syncs the static site
   - **Deploy to Render** triggers API + intelligence-engine redeploy hooks
3. Confirm:
   - `GET /api/health` → ok
   - `GET /api/intelligence/decision-engine-v2/health` → ok
   - Ask AGI shows institutional stack + constitutional decision

## Manual Render check

Ensure `TAVILY_API_KEY` remains set on `agib-intelligence-engine` (FAA live acquire).
Institutional stack flags are declared in `render.yaml` and default-on in Settings.
