# Filing Intelligence Layer (FIL) V1

**Architecture status:** v1.0.1 LOCKED  
**Primary question:** What do the company's own filings actually say?

Soft intelligence layer. No engine / UI / provider / Company Analysis / IC / CIO / RW / Academy / ACS / IRS / PIL redesign.

## Position

Official Filings → **FIL** → EIL → PIL → Analysts → IC → CIO → RW → ACS → IRS → Production

## Rule

Historical financial trends and company conclusions must originate from validated filing intelligence whenever available. Only official company documents are Tier 1 evidence.

## V1 corpus

Structured filing payloads (not PDF OCR):

- HDFC Bank Q1FY27 press release + earnings presentation + multi-year capital/CASA/NIM panel  
- Axis Bank Q1FY27 NIM  
- Nestlé India Q1FY27 BSE results  
- ICICI Bank funding stub (partially verified)

Append-only memory — duplicates rejected.

## Peer sync

`peer_sync.overlay_peer_series` upgrades PIL `seed_panel` → `live_filing` where FIL facts exist (soft-wire in `peer_intelligence.peer_database.packs`).

## Flags

`filing_intelligence` / `FILING_INTELLIGENCE`  
Sub: `fil_statements`, `fil_notes`, `fil_segments`, `fil_guidance`, `fil_risks`, `fil_management`, `fil_history`, `fil_evidence`

## APIs

- `GET /v1/filing-intelligence/company/{ticker}`
- `GET /v1/filing-intelligence/history/{ticker}`
- `GET /v1/filing-intelligence/timeline/{ticker}`
- `POST /v1/filing-intelligence/analyse`
- `GET /v1/filing-intelligence/evidence/{ticker}`
- `GET /admin/filing-intelligence`

## Soft-wire: Filing Diff Engine

FIL dashboard includes an additive `filing_diff` block. FDI consumes FIL extracts to answer “what changed?” without redesigning FIL.

## Next

Expand corpus via automated exchange/company PDF ingest — keep extractors; do not add analyst frameworks first.
