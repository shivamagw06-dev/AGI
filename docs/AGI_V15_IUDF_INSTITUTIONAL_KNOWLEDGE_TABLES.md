# AGIB V1.5 — Institutional Universe Data Factory (IUDF) & Institutional Knowledge Tables (IKT)

## Mission

Use the **uploaded equity universe file** (`EQUITY_L` → `NIFTYstocks.csv`) and the Nifty **index CSVs** as the single source of truth for AGIB's coverage universe. Never hardcode tickers or maintain parallel universe lists.

Documents are **evidence**. Structured tables are AGIB's **memory**. Research reads tables, not raw PDFs, whenever a table has the fact.

```text
Open Sources → Collect → Extract → Normalize → Write to Tables → Company Memory
             → Knowledge Graph → Research → Ask AGI
```

## What this ships (real, working now)

| Component | Module | Role |
|---|---|---|
| **Universe Master Registry** | `universe_master_registry/` | One row per company, sourced from `trading_universe` (EQUITY_L/NIFTYstocks) + `market_indices` (Nifty 50…Financial Services). No hardcoded list. |
| **Institutional Knowledge Tables (IKT)** | `institutional_knowledge_tables/` | 24 structured tables per the spec, **versioned** facts (`upsert_fact`), full history preserved, `current` flag per field. |
| **Coverage Matrix** | `coverage_matrix/` | Per-company boolean matrix (Financials / Annual Reports / Presentations / Transcripts / Shareholding / Corporate Actions / Research Ready) — *why* a company isn't ICC yet. |
| **Universe learning bootstrap** | `universe_learning/` | Seeds gather (CGL) + onboards every company's `company_master` row from the same universe files. |

## Universe Master Registry — fields

`company_name, ticker, isin, exchange, sector, industry, market_cap_category, index_membership, status, coverage_state, institutional_coverage, knowledge_confidence, research_ready, claim_safe, last_updated`

- `ticker / isin / exchange / industry / status` — **real**, from `EQUITY_L` / `NIFTYstocks.csv`.
- `index_membership` — **real**, from `indices/*.csv` (Nifty 50…Financial Services).
- `institutional_coverage / knowledge_confidence / research_ready / claim_safe` — **soft join** to `institutional_coverage_factory`. If ICF is unreachable, these stay `None` — **never a guessed value**.
- `sector / market_cap_category` — populated only once a real collector records them (via IKT); `None` until then.

New companies added to `NIFTYstocks.csv` / index CSVs are **onboarded automatically** — no code changes.

## Institutional Knowledge Tables — versioning contract

Every fact write is `upsert_fact(ticker, table, field, value, source=..., effective_date=..., period=...)`:

- **Never overwrites.** The prior version is marked `current: false`; a new version is appended.
- **`source` is mandatory.** Write fails without it — enforces evidence lineage, the "do not fabricate" rule at the API boundary.
- **Missing stays missing.** `get_table()` returns `null` for any field never written, plus a `missing_fields` list and `coverage_pct` — this *is* the "Missing Knowledge" signal per company/table.
- Period-keyed tables (financials, market data, shareholding, corporate actions, transcripts, presentations, annual reports, guidance) namespace facts by `<period>::<field>` so quarters/years don't collide.

Example — Capex Guidance revision (matches the proposed spec):

```text
upsert_fact("RELIANCE", "investor_presentations", "capex", "₹75,000 Cr",
            source="Q1 FY27 Investor Presentation", period="FY2027-Q1")
upsert_fact("RELIANCE", "annual_reports", "capex", "₹82,000 Cr",
            source="Annual Report FY27", period="FY2027")
```

Both versions persist; `get_field_history()` returns the full timeline; `get_table()` returns only the current value per period.

## The 24 tables (schema)

Company Master · Financial Statements · Market Data · Valuation · Shareholding · Corporate Actions · Investor Presentations · Earnings Call Transcripts · Annual Reports · Business Model · Management · Guidance · News · Risks · Catalysts · ESG · Macro Exposure · Competitors · Products · Customers · Contracts · Litigation · Credit Ratings · Knowledge Metadata

See `institutional_knowledge_tables/schema.py` (`TABLE_DEFS`) for the exact field list per table.

## Coverage Matrix

```text
GET /v1/coverage-matrix/company/{ticker}
GET /v1/coverage-matrix/universe?scope=nifty500&limit=20
```

Primary signal: ICF `score_evidence_classes` (real evidence-class presence). Fallback when ICF is unreachable: IKT table presence — narrower, but still real, never fabricated.

## APIs

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/universe-master-registry` | List (filter by `index`, paginate) |
| GET | `/v1/universe-master-registry/company/{ticker}` | Single company row |
| GET | `/v1/coverage-matrix/company/{ticker}` | Evidence-class matrix |
| GET | `/v1/coverage-matrix/universe` | Bounded matrix scan |
| GET | `/v1/institutional-knowledge-tables/tables` | Catalog (24 tables + fields) |
| GET | `/v1/institutional-knowledge-tables/company/{ticker}` | All populated tables for a company |
| GET | `/v1/institutional-knowledge-tables/company/{ticker}/{table}` | One table (current row/rows) |
| GET | `/v1/institutional-knowledge-tables/company/{ticker}/{table}/{field}/history` | Full version history |
| POST | `/v1/institutional-knowledge-tables/fact` | Write one versioned fact (requires `source`) |
| POST | `/v1/institutional-knowledge-tables/onboard-universe` | Onboard every company (`scope=nifty500\|all`) |
| POST | `/v1/institutional-knowledge-tables/company/{ticker}/rebuild` | Refresh `company_master` + `knowledge_metadata` |

Node BFF mirrors under `/api/intelligence/{universe-master-registry,coverage-matrix,institutional-knowledge-tables}/*`.

## Knowledge Operations actions

- `bootstrap_universe_learning` / `learn_universe` — seed CGL + onboard IKT `company_master`
- `rebuild_structured_tables` (ticker) — refresh one company's master + knowledge metadata
- `onboard_universe_tables` — onboard IKT `company_master` for the whole universe

## Update policy

- **On demand:** `onboard_universe` / `rebuild_structured_tables` for immediate refresh.
- **Continuous:** `universe_learning.bootstrap_universe_learning()` runs IKT onboarding on the same trigger as the CGL gather cycle, so structured `company_master` rows stay in sync with the universe file automatically.
- **Nightly (existing infra):** CGL / Historical Depth already run nightly per `render.yaml`; this release adds the IKT/registry layer on top — it does not change that schedule.

## Honest status — what's real vs scaffolded

| Table | Status |
|---|---|
| `company_master` | **Populated automatically** for every company in the universe file (ticker/ISIN/exchange/industry/status) |
| `knowledge_metadata` | **Soft-populated** from ICF (`icc_status_for`) when reachable; `None` otherwise |
| Remaining 22 tables (Financial Statements, Market Data, Valuation, Shareholding, Corporate Actions, Investor Presentations, Transcripts, Annual Reports, Business Model, Management, Guidance, News, Risks, Catalysts, ESG, Macro Exposure, Competitors, Products, Customers, Contracts, Litigation, Credit Ratings) | **Schema defined, write API ready.** Populated only as specific collectors are wired to call `upsert_fact(...)`. Until then, `get_table()` correctly reports them as missing — this is the intended "do not fabricate" behavior, not a bug. |

This is the deliberate design from the spec: *"Missing fields remain explicitly NULL rather than inferred."* The next phase is wiring existing collectors (FSE financial warehouse, ownership_intelligence shareholding, BSE corporate actions, IDI documents) to call `upsert_fact` so their output lands in these tables instead of only their own stores.

## Bulk company-info sheet upload (Excel/CSV)

Drop a spreadsheet with **one row per company** and columns like `Ticker`, `Company Name`, `Sector`, `Industry`, `CEO`, `CFO`, `PE`, `PB`, `Market Cap`, `ISIN`, `Website`, `Credit Rating`… Each recognized column becomes a versioned IKT fact.

**Where:** Admin → Knowledge Operations → **Upload Company Sheet** button (top toolbar). Or directly:

```bash
curl -X POST "$ENGINE/v1/institutional-knowledge-tables/upload-sheet" \
  -H 'content-type: application/json' \
  -d '{"filename":"companies.xlsx","content_base64":"<base64>","dry_run":true}'
```

**How it knows what to learn:**

1. Row resolution — a `Ticker`/`Symbol` column is matched against the uploaded universe registry (`trading_universe`); if absent, `Company Name` is matched by exact/substring search. **Rows that don't resolve are reported, never guessed.**
2. Column mapping — headers are normalized and matched against a known map (`institutional_knowledge_tables/bulk_sheet.py:_COLUMN_MAP`) to `(table, field)`. Unrecognized columns are listed as `unmapped_columns`, not silently dropped or guessed.
3. Every non-blank cell is written via `upsert_fact(ticker, table, field, value, source="bulk_upload:<filename>", ...)` — versioned, never overwritten.
4. `dry_run: true` previews the resolution + mapping without writing anything — use this first.

Response includes `resolved_count`, `unresolved_rows` (with reasons), `mapped_columns`, `unmapped_columns`, and `fields_written_total` so you can see exactly what happened before trusting the data.

## Success criteria

- [x] Universe Master Registry sourced from the uploaded file, not a hardcoded list
- [x] New companies in the file are onboarded automatically (no code changes)
- [x] Every value has evidence lineage (`source` mandatory on write)
- [x] Missing fields stay explicitly `NULL`, never inferred
- [x] Field history preserved — nothing is overwritten
- [x] Coverage Matrix gives an operational view of *why* a company isn't ICC
- [ ] All 24 tables populated by dedicated collectors (in progress — schema + write API done; collector wiring is the next phase)
- [ ] Admin "Structured Data Explorer" UI (API-complete; frontend page not yet built)
