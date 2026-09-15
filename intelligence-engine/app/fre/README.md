# FRE — Finance Retrieval Engine v1.0

Institutional **intelligence acquisition** layer for AGIB.

FRE is **not** a chatbot, scraper UI, or generic search box.  
It continuously gathers, validates, structures, indexes and **serves evidence** to the AGIB Intelligence Engine.

## Position (v1.0.1 LOCKED — additive soft-wire)

```text
FAA (Acquire public docs)
        ↓
       FRE   ← query understanding → multi-task plan → retrieve/rank evidence
        ↓
 Evidence + provenance + KG links
        ↓
 soft into CAE / KIP / Ask AGI
        ↓
 IRP / RSP / Decision Engine (reasoning — not FRE)
```

Live downloading belongs to **FAA**, not FRE. FRE searches/ranks the index FAA fills.

## Invariants

1. FRE **never answers** the user.
2. Every claim requires provenance (source, document, section/page).
3. Prefer Tier‑1/2 authoritative sources over general web.
4. Deduplicate by checksum; version documents.
5. Flag contradictions across sources.
6. Soft-wire only — no redesign of AOI, EVE, KF, KC, KIP, CAE, Ask AGI.

## Pipeline

Intent → Entities → Query Plan → Source Router → Acquire → Parse → Clean → Chunk → Embed → Hybrid Search → Re-rank → Evidence → Cross-validate → Knowledge Graph → Serve

## APIs (`/v1/fre/*`)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Programme health + flags |
| `GET /dashboard` | Ops snapshot |
| `GET /query?q=` | Full evidence pack |
| `GET /search?q=` | Hybrid search hits |
| `GET /company/{key}` | Company evidence + timeline |
| `GET /document/{id}` | Document + chunks |
| `GET /evidence` | Evidence list |
| `GET /timeline` | Publication timeline |
| `GET /news` | News-tier documents |
| `GET /graph` | Knowledge graph |
| `POST /ingest` | Ingest a document payload |
| `POST /jobs` | Soft continuous-ingest cycle |
| `GET /consult?q=` | Ask AGI / CAE soft retrieval |

Node BFF mirrors these under `/api/intelligence/fre/*`.

## Authority tiers

1. Company IR / Annual / Quarterly / Filings  
2. NSE · BSE · SEBI · RBI · Government  
3. World Bank · IMF · OECD · FRED  
4. Trusted financial news  
5. Industry / trade / research  
6. General web (last resort)

## Runtime notes

- In-memory store first (same pattern as KIP/FLE).
- Embeddings reuse KIP hashing vectors (dim 256) — no external embedding API required.
- Soft-calls AOI when bound; seeds an institutional corpus for offline evidence.
- Optional soft-publish into KIP when `FRE_SOFT_PUBLISH_KIP` is enabled.
