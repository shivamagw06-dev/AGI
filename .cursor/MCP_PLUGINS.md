# AGIB Cursor MCP Plugins

Project MCP config: `.cursor/mcp.json`  
Runtime acquisition keys (already used by FAA): `EXA_API_KEY`, `FIRECRAWL_API_KEY`, `BROWSERBASE_API_KEY` on Render / local `.env`.

## Status map

| Plugin | Role for AGIB | Cursor MCP | AGIB runtime already |
|--------|---------------|------------|----------------------|
| **Exa** | AI-native web / company research | Configured → needs your `EXA_API_KEY` | Yes — FAA search |
| **Firecrawl** | Crawl IR/SEC/PDF → markdown | Configured → needs `FIRECRAWL_API_KEY` | Yes — FAA enrich |
| **Context7** | Latest library/API docs while coding | Configured → optional `CONTEXT7_API_KEY` | N/A (dev-only) |
| **Browserbase** | Cloud browser for JS sites | Configured → needs Browserbase + Gemini keys | Partial — Playwright + optional Browserbase in FAA |
| **Supabase** | DB / auth / CMS from Cursor | Configured → **Authenticate in Cursor Settings → MCP** | Yes — CMS, newsletter, nifty500 |
| **Render** | Deploy / restart / logs | Configured → needs `RENDER_API_KEY` | Deploy via Git + Dashboard |
| **MongoDB** | — | **Skip** | Not used |
| **Pinecone** | Optional vector DB MCP | Configured but **optional** | Prefer **pgvector via Supabase** (already in stack) |
| **Postman** | API regression | Use collection below (no MCP required) | Node BFF + IE routes |

## Enable in Cursor Desktop (required)

1. Put API keys in your shell env or Cursor env (never commit secrets):
   - `EXA_API_KEY`
   - `FIRECRAWL_API_KEY`
   - `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID`
   - `GEMINI_API_KEY` (Browserbase Stagehand model)
   - `RENDER_API_KEY` ([Render → Account → API Keys](https://dashboard.render.com/u/settings#api-keys))
   - `CONTEXT7_API_KEY` (optional)
   - `PINECONE_API_KEY` only if you opt into Pinecone
2. Open **Cursor Settings → MCP**.
3. Confirm green status for each server.
4. For **Supabase**: click **Connect / Authenticate** (OAuth) — tools stay locked until you do.
5. Fully quit and reopen Cursor if a server stays red.

### One-click Render install (alternative)

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=render&config=eyJ1cmwiOiJodHRwczovL21jcC5yZW5kZXIuY29tL21jcCIsImF1dGgiOnsiQ0xJRU5UX0lEIjoiY3Vyc29yIn19
```

## Cloud Agent note

This cloud run already sees **Exa** + **Supabase** (Supabase needs your desktop auth) + **cursor-cloud**.  
Firecrawl / Context7 / Browserbase / Render / Pinecone activate after Desktop MCP config + keys.

## Postman

Import `postman/AGIB_Intelligence.postman_collection.json`.  
Set collection variables:

- `API` = `https://finance-news-backend-19i5.onrender.com`
- `IE` = `https://agib-intelligence-engine.onrender.com`

## Recommendation

| Priority | Action |
|----------|--------|
| P0 | Auth **Supabase** MCP + set **Exa** / **Firecrawl** keys (research + CMS) |
| P0 | Add **Render** API key (restart/debug cold starts without leaving Cursor) |
| P1 | **Browserbase** if Playwright on Free Render is flaky for JS IR pages |
| P1 | **Context7** for faster library work |
| Skip | MongoDB |
| Skip for now | Pinecone — stay on Supabase **pgvector** unless you need a separate vector product |

## Architecture rule

MCP plugins help **Cursor agents**. Production Ask AGI still uses FAA soft-wires (`EXA` / `FIRECRAWL` / Playwright / Browserbase) inside the intelligence engine — not Cursor MCP at request time.
