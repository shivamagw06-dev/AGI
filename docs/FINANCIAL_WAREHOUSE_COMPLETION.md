# Phase 7.4F — Institutional Financial Warehouse Completion Programme (FWCP) v1.0

## Vision

AGIB’s intelligence stack (UVE, HVIE, VPAE, VARIE, RIE, FIE, MIE, IFAC) is already in place.
The remaining limitation is **warehouse coverage**, not intelligence logic.

Phase 7.4F completes the Institutional Financial Warehouse so every listed company has the
statement, share-count, ownership, peer, profile and consensus inputs those engines need.

**This phase does not create new intelligence.** It improves warehouse completeness.

## Targets

| Metric | Target |
|--------|--------|
| Annual statement coverage | ≥95% |
| Quarterly statement coverage | ≥95% |
| Share count coverage | ≥99% |
| Company financial coverage | ≥95% |
| Consensus coverage | ≥90% |
| Ownership coverage | ≥90% |
| HVIE eligible | ≥95% |
| HVIE completion | ≥90% |

## Hard rule

Never import vendor historical PE / PB / EV. Those remain **HVIE reconstructions** from:

`daily_market_history + financials_* + corporate_actions + share_count_history + VPAE`

## Data packs

1. **Company master** — identity, ISIN, sector/industry, listing, description (existing tab)
2. **Annual statements** — `financials_annual` (≥3 years minimum; prefer 10)
3. **Quarterly statements** — `financials_quarterly` (≥4 periods minimum; prefer 20)
4. **Share count history** — new `share_count_history` tab (basic / diluted / weighted / outstanding)
5. **Consensus** — `consensus` (reference for FIE)
6. **Ownership** — `ownership`
7. **Peers** — `peer_relationships`
8. **Profiles** — `profile_history`

## Sources

**Primary:** Capital IQ (via IKT refresh), Upstox Fundamentals, Financial Connector  
**Secondary:** Yahoo Finance statements/history, existing warehouse rows  
**Validation:** Formula Engine + warehouse DQIV + FWCP DQIV rules

## Import pipeline

```text
Capital IQ / Upstox / Yahoo / Connector
        ↓
   Import Queue (fwcp_import_queue)
        ↓
   Normalizer (units + statement identity)
        ↓
   FWCP DQIV
        ↓
   Warehouse gateway.write
        ↓
   Coverage board + HVIE eligibility
```

## Upstox-first fill (preferred on Render)

Yahoo fundamentals are often **empty from datacenter IPs**. Prefer Upstox:

| Method | Path |
|--------|------|
| GET | `/v1/warehouse/upstox-fill/queue` |
| GET | `/v1/warehouse/upstox-fill/board` |
| POST | `/api/upstox/statements/fill-empty` |
| POST | `/api/upstox/statements/fill-empty/run` |
| POST | `/api/upstox/statements/fill-empty/stop` |

Calls `GET /v2/fundamentals/{isin}/income-statement|balance-sheet|cash-flow` with
`type=consolidated`, `time_period=yearly|quarterly`, `fs=true`. Units: crore → INR million.
Queue: EMPTY → MINIMAL → thin, **INE\* ISIN only** (skips INF\* funds).

Admin: `/admin/financial-coverage` → **Start Upstox fill**.

## Yahoo-first fill (fallback)

After Step 0, Yahoo Finance can fill EMPTY / thin companies when egress allows:

| Method | Path |
|--------|------|
| GET | `/v1/warehouse/yahoo-fill/status` |
| GET | `/v1/warehouse/yahoo-fill/board` |
| GET | `/v1/warehouse/yahoo-fill/queue` |
| POST | `/v1/warehouse/yahoo-fill/start` |
| POST | `/v1/warehouse/yahoo-fill/run` |
| POST | `/v1/warehouse/yahoo-fill/stop` |
| POST | `/v1/warehouse/yahoo-fill/{symbol}` |

**Honest ceiling:** Yahoo ≈4–5 annual years and ≈4–6 quarters. Enough to clear EMPTY → PARTIAL for most equities. **Not** enough for COMPLETE_10Y — CapIQ / filings still required for 10y depth.

Admin controls live on `/admin/financial-coverage` (Start Yahoo fill).

## Step 0 — Financial Warehouse Coverage Audit (read-only)

Before CapIQ / provider import, measure what already exists.

| Classification | Annual | Quarters |
|----------------|--------|----------|
| COMPLETE_10Y | ≥8 years | ≥40 |
| GOOD | 6–9 years | 24–39 |
| PARTIAL | 3–5 years | 8–23 |
| MINIMAL | 1–2 years | sparse |
| EMPTY | none | none |

Audit answers: % with ≥10y annual, % with ≥40 quarters, who needs backfill, weakest sectors, most-missing fields. **No data is modified.**

Admin: `/admin/financial-coverage`

## APIs

| Method | Path |
|--------|------|
| GET | `/v1/fwcp/health` |
| GET | `/v1/warehouse/financial-coverage` |
| GET | `/v1/warehouse/financial-audit` |
| GET | `/v1/warehouse/coverage/summary` |
| GET | `/v1/warehouse/coverage/sector` |
| GET | `/v1/warehouse/missing-financials` |
| GET | `/v1/warehouse/company/{symbol}/coverage` |
| GET | `/v1/warehouse/missing-statements` |
| GET | `/v1/warehouse/missing-share-count` |
| GET | `/v1/warehouse/import/status` |
| GET | `/v1/warehouse/import/board` |
| POST | `/v1/warehouse/import/start` |
| POST | `/v1/warehouse/import/stop` |
| POST | `/v1/warehouse/import/resume` |
| POST | `/v1/warehouse/import/retry` |
| POST | `/v1/warehouse/import/run` |
| POST | `/v1/warehouse/share-count/{symbol}/sync` |

BFF mirrors under `/api/intelligence/…`.

## Admin

- `/admin/financial-coverage` — Step 0 audit (histograms, sector gaps, missing fields, import queue)
- `/admin/financial-warehouse` — import runtime board, Start / Resume / Retry / Run batch

## Package

`intelligence-engine/financial_warehouse_completion/`

- `audit.py` — Step 0 read-only coverage audit  
- `yahoo_fill.py` — Yahoo-first EMPTY/thin statement fill + share harvest  
- `coverage.py` — universe / company / gap metrics  
- `share_count.py` — harvest + write `share_count_history`  
- `dqiv_rules.py` — share-count & statement reject rules  
- `import_runtime.py` — bootstrap / daily / retry worker  
- `capital_iq_import.py` — CapIQ→warehouse stage wrapper  
- `production.py` — API facade  

## Downstream

No engine logic changes required beyond HVIE eligibility reading `share_count_history`.
Once coverage rises, HVIE / RIE / FIE / VARIE / MIE / IFAC / Ask deepen automatically.

## End state

The warehouse is AGIB’s authoritative financial foundation. HVIE no longer stalls on missing
statements or share counts at scale, and research answers stop explaining “history unavailable”
when the only gap was incomplete warehouse inputs.
