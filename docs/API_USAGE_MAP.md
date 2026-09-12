# AGIB API usage map

Where each key actually runs. If a key is listed but **unused**, setting it in Render/Hostinger does nothing until code wires it.

## Product surfaces

| Surface | Backend path | Keys that power it |
|---------|--------------|--------------------|
| Macro Intelligence page | `GET /api/market/macro-briefing` | `FRED_API_KEY`, `ALPHAVANTAGE_API_KEY`, `INDIANAPI_KEY`, optional `OPENAI_API_KEY` |
| **Ask AGI Economist** | `POST /api/market/macro-ask` | `OPENAI_API_KEY` (+ same macro context as above) |
| Intelligence Engine badge | `GET /api/intelligence/health` | `INTELLIGENCE_ENGINE_URL`, `INTELLIGENCE_ENGINE_TOKEN` |
| Market Intelligence / pulse | `GET /api/market/*` | `GROWW_*`, optional OpenAI |
| Pre-Market | `GET /api/market/pre-market-briefing` | `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`, Groww |
| News headlines | `GET /api/news/headlines` | `NEWSAPI_KEY` |
| Deals / research AI | `server/research.js` | `PERPLEXITY_KEY` |
| Nifty / NSE research worker | `server/scripts/nifty500_research_engine.py` | `GROWW_ACCESS_TOKEN`, `SUPABASE_*` |
| CMS / auth / portal | Supabase | `VITE_SUPABASE_*`, `SUPABASE_SERVICE_ROLE_KEY` |

Frontend must call the **Render API** (`VITE_API_URL`), not Hostinger static hosting. Default production origin: `https://finance-news-backend-19i5.onrender.com`.

## Keys you provided — status

| Key | Status | Used in |
|-----|--------|---------|
| `GROWW_ACCESS_TOKEN` / `GROWW_API_KEY`+`SECRET` | **USED** | Market data, Nifty research worker |
| `SUPABASE_URL` + service role / anon | **USED** | CMS, research publish, auth |
| `OPENAI_API_KEY` | **USED** | Macro / market / pre-market narrative + **Ask AGI Economist** |
| `FRED_API_KEY` | **USED** | Macro rates / CPI |
| `ALPHAVANTAGE_API_KEY` | **USED** | Macro gold / WTI |
| `INDIANAPI_KEY` | **USED** | India commodities / market context |
| `NEWSAPI_KEY` | **USED** | Headline strip |
| `PERPLEXITY_KEY` | **USED** | Deal tracker / research |
| `FINNHUB_API_KEY` | **USED** (pre-market) | Not yet in macro fetchers |
| `TWELVE_DATA_API_KEY` | **USED** (pre-market) | Not yet in macro fetchers |
| `INTELLIGENCE_ENGINE_URL` + `TOKEN` | **USED** | Python multi-agent desk (must be a live Render service) |
| `POLYGON_API_KEY` | **UNUSED** | Listed in `.env.example` only |
| `FMP_API_KEY` | **UNUSED** | Listed only |
| `RBI_DATA_API_KEY` | **UNUSED** | Listed only |
| `EXCHANGERATE_API_KEY` | **UNUSED** | Listed only |

## Why Macro shows “Intelligence Engine offline”

Node probes `INTELLIGENCE_ENGINE_URL` → Python `/v1/health`.

Current Render probe returns: `fetch failed` / start engine on that URL.

The **deterministic desk still works** (macro briefing from FRED/AV/etc.). Offline only means the Python multi-agent service is not reachable.

**Fix on Render:** deploy `agib-intelligence-engine` from `render.yaml`, set `INTELLIGENCE_ENGINE_URL` on `agib-api` to that service host, share `INTELLIGENCE_ENGINE_TOKEN`.

## Why Ask / Open Intelligence felt dead

1. **Ask AGI Economist** used to only reshuffle local briefing text in the browser — no API call. It now posts to `/api/market/macro-ask` (OpenAI + macro context).
2. **Open Intelligence** now routes to `/beta` (AGI Intelligence workspace).
3. If the static Hostinger site was calling `/api/*` on itself (no `VITE_API_URL`), requests returned HTML and UI looked broken. Frontend now defaults production API origin to the Render gateway.
