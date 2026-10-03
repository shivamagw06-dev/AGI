# Peer Intelligence Layer (PIL) V1

**Architecture status:** v1.0.1 LOCKED  
**Primary question:** How does this company compare to the best and most relevant peers?

Soft intelligence layer. No engine / UI / provider / Company Analysis / IC / CIO / RW / Academy / ACS / IRS redesign.

## Rule

Never write standalone observations:

> "HDFC has a strong deposit franchise."

Always write relative intelligence:

> "HDFC's CASA ratio ranks 2nd among Indian private banks, but has declined from its own multi-year average while ICICI's funding mix has remained more stable."

## Packs (V1)

- `banks_india_v1` — HDFC / ICICI / Axis / Kotak / SBI + global banks  
- `fmcg_india_v1` — Nestlé India / HUL / Britannia / Dabur / ITC + globals  
- `it_services_v1` — TCS / Infosys / HCL / Wipro / TechM + globals  
- `consumer_internet_v1` — Eternal / Swiggy / Nykaa / Paytm + Uber / DoorDash / MELI  

Multi-year peer panels are `seed_panel` unless marked mixed with EIL filing points. Gaps stay visible.

## Flags

`peer_intelligence` / `PEER_INTELLIGENCE`  
Sub: `pil_peers`, `pil_history`, `pil_percentiles`, `pil_rankings`, `pil_benchmarks`, `pil_commentary`, `pil_scorecards`

## APIs

- `GET /v1/peer-intelligence/health`
- `GET /v1/peer-intelligence/dashboard`
- `GET /v1/peer-intelligence/company/{ticker}`
- `GET /v1/peer-intelligence/compare`
- `POST /v1/peer-intelligence/analyse`
- `GET /v1/peer-intelligence/history/{ticker}`
- `GET /v1/peer-intelligence/rankings`
- `GET /v1/peer-intelligence/quality-gates`
- `GET /admin/peer-intelligence`

## Soft-wires

- IRS dashboard: `soft_slice_for_irs`
- EIL dashboard: `soft_slice_for_eil`
- Analysts: `soft_slice_for_analyst(ticker, analyst=…)`

## Soft-wire: Filing Intelligence Layer

When FIL is enabled, pack loaders overlay `live_filing` points onto seed series via `filing_intelligence.peer_sync.overlay_peer_series`.

## Next

Expand FIL corpus so remaining seed peers become live filing panels — do not add more analyst frameworks first.
