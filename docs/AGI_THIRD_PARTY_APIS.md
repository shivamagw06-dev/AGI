# AGI — Third-Party API Inventory & Credential Status

**Probed:** 2026-07-28 from the cloud agent VM. Columns separate *wired in code* from *usable right now*.

## Environment credential status (this VM)

| Credential | Present | Live check |
|------------|:-------:|------------|
| `OPENAI_API_KEY` | yes | **200 OK** on `/v1/models` — working |
| `GEMINI_API_KEY` | yes | **400 "API key not valid"** — key is set but rejected |
| `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` | yes | **200 OK** on `/auth/v1/settings` — working (anon scope) |
| `SUPABASE_SERVICE_ROLE_KEY` | no | server-side admin/DB writes unavailable |
| All other provider keys | no | providers skip and fall back |

Outbound network from this VM works (World Bank 200, BSE 200, Resend host 200). Yahoo returned 429 (rate limit) and `nseindia.com` did not respond — NSE commonly blocks datacentre IPs.

## No-key providers (work without credentials)

| Provider | Host | Category | Status here |
|----------|------|----------|-------------|
| Yahoo Finance | `query1/query2.finance.yahoo.com` | market data | reachable, 429 rate-limited |
| World Bank | `api.worldbank.org/v2` | macro | 200 OK |
| Frankfurter (ECB FX) | `api.frankfurter.app` | macro/FX | reachable |
| Open-Meteo | `api.open-meteo.com` | macro | reachable |
| BSE | `bseindia.com`, `api.bseindia.com` | market data / filings | 200 OK |
| NSE | `nseindia.com`, `nsearchives.nseindia.com` | market data / filings | blocked from this IP |
| RBI / DBIE | `rbi.org.in`, `dbie.rbi.org.in` | macro / documents | live in LIDI collectors |
| SEBI / MoF / MOSPI / PIB / IMF | various gov | documents / macro | seeded (synthetic) in AOI |
| Company IR sites | infosys.com, tcs.com, ril.com, hdfcbank.com, wipro.com | documents | live in LIDI; seeded in AOI |
| DuckDuckGo HTML | `html.duckduckgo.com` | search | needs Playwright Chromium |
| Trendlyne widget | `trendlyne.com` | frontend embed | client-side |

## Key-required providers (wired, currently inactive)

| Provider | Host | Env var(s) | Category |
|----------|------|-----------|----------|
| Groww | `api.groww.in/v1` | `GROWW_ACCESS_TOKEN` / `GROWW_API_KEY` + `GROWW_API_SECRET` | market data (Node primary) |
| IndianAPI | `stock.indianapi.in` | `INDIANAPI_KEY` / `INDIAN_API_KEY` | market data |
| Finnhub | `finnhub.io/api/v1` | `FINNHUB_API_KEY` | market data |
| Financial Modeling Prep | `financialmodelingprep.com/api/v3` | `FMP_API_KEY` | market data |
| Twelve Data | `api.twelvedata.com` | `TWELVE_DATA_API_KEY` | market data (pre-market) |
| FRED | `api.stlouisfed.org/fred` | `FRED_API_KEY` | macro |
| Alpha Vantage | `alphavantage.co` | `ALPHAVANTAGE_API_KEY` | macro |
| NewsAPI | `newsapi.org/v2` | `NEWSAPI_KEY` | news |
| Perplexity | `api.perplexity.ai` | `PERPLEXITY_KEY` / `PERPLEXITY_API_KEY` | search + LLM |
| Google Gemini | `generativelanguage.googleapis.com` | `GEMINI_API_KEY` (+ aliases) | LLM / editorial writer |
| OpenAI | `api.openai.com/v1` | `OPENAI_API_KEY` | LLM |
| Exa | `api.exa.ai` | `EXA_API_KEY` | search |
| Firecrawl | `api.firecrawl.dev` | `FIRECRAWL_API_KEY` | crawl / documents |
| Browserbase | `api.browserbase.com` | `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` | headless fetch |
| Tavily | `api.tavily.com` | `TAVILY_API_KEY` | search |
| SerpAPI | `serpapi.com` | `SERPAPI_API_KEY` / `SERPAPI_KEY` | search |
| Bing Web Search | `api.bing.microsoft.com` | `BING_SEARCH_API_KEY` | search |
| Google CSE | `googleapis.com/customsearch/v1` | `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID` | search |
| Resend | `api.resend.com` | `RESEND_API_KEY` | email |
| SendGrid | SDK | `SENDGRID_API_KEY` | email fallback |
| Supabase | `{project}.supabase.co` | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, anon keys | auth + DB |
| Free Stock API | `FREE_STOCK_API` host | `FREE_STOCK_API` | market data proxy |

## Declared but not implemented

No HTTP client exists for these; they appear only in registries or `.env.example`:

- Polygon (`POLYGON_API_KEY`)
- SEC EDGAR
- ExchangeRate API (`EXCHANGERATE_API_KEY`) — Frankfurter used instead
- Authenticated RBI API (`RBI_DATA_API_KEY`)
- Licensed consensus feed (`AGIB_LICENSED_CONSENSUS_PROVIDER`) — stub
- `PINECONE_API_KEY`, `CONTEXT7_API_KEY`, `RENDER_API_KEY` — dev/MCP tooling only

## Default live-vs-seeded posture

| Subsystem | Default | Enable live with |
|-----------|---------|------------------|
| AOI (public acquisition) | seeded/synthetic | `AOI_LIVE_FETCH=true` |
| FAA (fetch/acquire) | offline stub | `FAA_LIVE_FETCH=true` + a search key |
| KF collectors | fixtures | `KF_LIVE_GROWW` / `KF_LIVE_NSE` / `KF_LIVE_YAHOO` |
| LIDI live-data | **live HTTP** | recorded samples via `LIDI_ALLOW_RECORDED_SAMPLE` (dev only) |
| Market Data Platform | Yahoo live; others skipped | set IndianAPI/Finnhub/FMP keys |
| LLM / editorial | deterministic templates | valid `GEMINI_API_KEY` or `OPENAI_API_KEY` |

Global config: `live=False`, `backtest=True` — backtest/validation is the platform default.

## Architecture rule

Python engines must not call vendors directly. They read cached Node gateway routes via `AgibClient` (`AGIB_API_BASE_URL`, `AGIB_SERVICE_TOKEN`), or go through `app/market_data/` (failover + circuit breakers), `live_data/` collectors, and `app/faa/`.
