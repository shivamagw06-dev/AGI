# Filing Diff Engine (FDI) V1

**Architecture status:** v1.0.1 LOCKED  
**Primary question:** What materially changed since the previous filing?

Soft layer. No engine / UI / provider / FIL / EIL / PIL / Company Analysis / IC / CIO / RW / ACS / IRS redesign.

## Position

Official Filings → FIL → **FDI** → EIL → PIL → Analysts → IC → CIO → RW → ACS → IRS → Production

## Rule

Do not summarise the latest filing. Explain what changed, why it matters, thesis impact (never Buy/Sell), and committee follow-ups — with evidence links to current and previous documents.

## Thesis Impact Matrix

Every material change maps to the investment case:

| Filing Change | Business | Financial | Valuation | Risk | Committee |
|---|---|---|---|---|---|
| NIM ↓ | ◐ | ✅ | ✅ | ◐ | Review |
| CASA ↓ | ✅ | ✅ | ◐ | ◐ | Review |
| Buyback announced | ◐ | ✅ | ✅ | ❌ | Note |
| New regulatory risk | ◐ | ❌ | ◐ | ✅ | Escalate |

✅ primary · ◐ secondary · ❌ not material · Committee: Review / Escalate / Note / Monitor

Used by Analyst → Committee → CIO routing (`soft_slice_for_analyst`).

## Flags

`filing_diff_engine` / `FILING_DIFF_ENGINE`  
Sub: `fdi_statements`, `fdi_guidance`, `fdi_risks`, `fdi_management`, `fdi_segments`, `fdi_accounting`, `fdi_capital`, `fdi_governance`, `fdi_ownership`

## APIs

- `GET /v1/filing-diff/company/{ticker}`
- `POST /v1/filing-diff/analyse`
- `GET /v1/filing-diff/timeline/{ticker}`
- `GET /v1/filing-diff/changes/{ticker}`
- `GET /admin/filing-diff`
