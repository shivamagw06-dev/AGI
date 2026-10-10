# AGI Institutional Data Warehouse

The warehouse is AGI's central intelligence database and the admin workspace on
top of it. The workspace looks and behaves like Excel. Nothing about it is a
spreadsheet: every sheet is a database table, every edit is versioned, every
imported value keeps its provenance, and every calculation runs on the server.

```
Collectors → Validation → Warehouse → Admin Workspace → Historical Database
                                   ↓
        UKO → Ask AGI → Valuation Terminal → Hedge Fund → Research Intelligence
```

- **Backend package** `intelligence-engine/institutional_warehouse/`
- **Admin page** `/admin/data-warehouse` (`src/pages/admin/DataWarehouse.jsx`)
- **Engine API** `/v1/warehouse/*` · **BFF** `/api/intelligence/warehouse/*`
- **Acceptance** `intelligence-engine/scripts/warehouse_acceptance_v1.py`

---

## Storage

SQLite by default, PostgreSQL/Supabase when a URL is supplied. The store layer
speaks one dialect-neutral SQL subset, so the same code runs on both.

| Setting | Purpose | Default |
|---|---|---|
| `INSTITUTIONAL_WAREHOUSE_ROOT` | Data directory | `$KIP_DATA_DIR/institutional_warehouse` or `intelligence-engine/data/institutional_warehouse` |
| `WAREHOUSE_DATABASE_URL` | Postgres/Supabase connection | unset → `sqlite:///<root>/warehouse.sqlite3` |
| `WAREHOUSE_DAILY_REFRESH` | Run the daily pipeline in the gather worker | `true` on the worker, `false` elsewhere |
| `WAREHOUSE_REFRESH_AT` | Daily slot, 24h IST | `18:45` |
| `WAREHOUSE_DEFAULT_ROLE` | Role for an admin not listed explicitly | `publish` |
| `WAREHOUSE_READERS` / `_EDITORS` / `_APPROVERS` / `_PUBLISHERS` | Comma-separated identities per role | unset |

Physical tables are `wh_<tab_id>` plus six ledgers: `wh_audit`,
`wh_cell_versions`, `wh_row_snapshots`, `wh_overrides`, `wh_imports`,
`wh_refresh_runs`. Tables are created and upgraded on first use — adding a
column to `schema.py` is the whole migration.

---

## The fourteen tabs

| # | Tab | Mode | Natural key | Filled by |
|---|---|---|---|---|
| 1 | Company Master | master | `company_id` | Yahoo universe, Capital IQ |
| 2 | Daily Market History | append | `symbol + date` | NSE bhavcopy, Yahoo, KF monthly history |
| 3 | Financials (Annual) | append | `symbol + fiscal_year` | Knowledge Factory, Capital IQ LTM, FSE |
| 4 | Financials (Quarterly) | append | `symbol + fiscal_period` | Knowledge Factory, FSE |
| 5 | Historical Ratios | calculated | `symbol + period` | formula engine |
| 6 | Historical Valuation | calculated daily | `symbol + date` | Yahoo multiples + formula engine |
| 7 | Consensus | append | `symbol + consensus_date` | Capital IQ consensus |
| 8 | Research Intelligence | structured | `symbol + document_type + fiscal_period` | research corpus |
| 9 | Research Timeline | append | `symbol + date + event` | KF timeline, LIDI events, CGL |
| 10 | Corporate Actions | append | `symbol + action_date + action_type` | KF actions, LIDI announcements |
| 11 | Ownership | append | `symbol + as_of` | KF shareholding |
| 12 | Hedge Fund Factors | calculated | `symbol + as_of` | formula engine |
| 13 | Company Intelligence | generated | `symbol` | CGL extracts, admin review |
| 14 | Data Quality | internal | `table_id` | validation engine |

Mode drives behaviour, not decoration:

- **append** tabs key on a period, so a re-import writes the next period rather
  than rewriting the last one. History is never overwritten.
- **calculated** tabs refuse manual edits at the API, not just in the UI.
- Row identity is a deterministic hash of the natural key, so the same fact from
  two collectors lands on one row instead of duplicating.

---

## Provenance, overrides and versions

Three separate ideas, deliberately not merged:

1. **Imported value** lives in the tab table with `source` and `last_updated`.
   An admin edit never touches it.
2. **Override** lives in `wh_overrides`. Reads overlay active overrides on top
   of the imported row and report which columns were overridden and by whom.
   Clearing an override falls straight back to the imported value.
3. **Version** lives in `wh_cell_versions` (old value, new value, actor, reason,
   source, version) and `wh_row_snapshots` (the whole row at that version, for
   diff and restore).

This is why an admin correction can never silently destroy what a collector
gathered, and why any row can be compared with — or rolled back to — an earlier
state.

---

## Server-side formulas

No spreadsheet formulas exist anywhere in the product. `formulas.py` computes:

```
Free Cash Flow = CFO − Capex
Book Value     = Equity / Shares Outstanding
Market Cap     = Close × Shares Outstanding
ROE            = PAT / Average Equity
Upside         = (Target Price − CMP) / CMP
Relative Score = 0.50 × sector percentile + 0.25 × consensus + 0.25 × profitability
```

Two rules keep the numbers honest:

- **Overrides feed the formulas.** A corrected PAT changes the ratio that
  depends on it, because the engine reads effective rows.
- **Vendors own their multiples.** When Yahoo or Capital IQ reports P/E, P/B,
  EV/EBITDA and the rest, the warehouse keeps that value rather than
  re-deriving it from a statement of uncertain vintage. The warehouse computes
  what only it can see: sector and industry medians, the percentile, the
  relative valuation score, enterprise value, upside and factor scores.

Recalculation runs after every import and edit, scoped to the stages that the
changed tab actually affects.

---

## Validation

`validate_payload` runs before an import commits; `validate_tab` audits what is
already stored and drives the Data Quality tab.

The engine separates two severities, which matters more than it sounds:

- **Impossible → reject.** Holdings outside 0–100%, promoter plus public beyond
  the float, a low above the high, a future trading date, a malformed symbol, a
  duplicate natural key inside one batch, a missing key column.
- **Suspicious → warn and store.** A margin above 100%, an extreme multiple, an
  ISIN that fails its checksum shape, a company that is not yet in Company
  Master. These are real often enough that rejecting them would silently lose
  data.

Indian shareholding convention is modelled explicitly: promoter plus public sums
to 100, and the institutional buckets are a slice of the public float rather
than an addition to it.

---

## Financial statement identity

A consolidated and a standalone filing for one company and year are two
different facts, not two opinions about one fact. Until `statement_type` joined
the natural key they hashed to the same row, so importing one silently replaced
the other — no conflict, no warning, no history.

Both financial tabs are now keyed by statement type:

```
financials_annual     (symbol, statement_type, fiscal_year)
financials_quarterly  (symbol, statement_type, fiscal_period)
```

### What is deliberately not in the key

**`source`.** Conflict detection works by finding the stored row an incoming row
collides with. If each vendor owned its own row they would never collide, and
DQIV could never report that Yahoo and Upstox disagree about the same filing.
Sources share a row; disagreements are recorded rather than avoided.

**`statement_version`.** Every write already snapshots the prior row through
`versions`, so a restatement is a new snapshot on the same identity. Putting a
version in the key would stand up a second version chain competing with the one
that exists.

### Defaulting

`statement_type` is required by the key, and `store.make_row_id` refuses a row
with an empty key part, so the gateway fills it before the row is keyed. A
collector that declares nothing lands as `UNKNOWN` rather than being dropped.
An unrecognised vendor label also becomes `UNKNOWN` rather than being guessed —
a filing recorded under the wrong type is worse than one recorded under none,
because it would be compared against the wrong sibling.

Conflict detection additionally refuses to compare rows whose type or frequency
differ, so a legacy mis-pairing cannot surface as a false disagreement.

### Migrating rows written before this

Legacy rows have no type *and* a `row_id` hashed from the old key, so a later
import of the same filing would compute a different id and insert a duplicate
beside it. The migration does both: stamps `UNKNOWN` and re-keys.

```bash
GET  /v1/warehouse/statement-identity                            # what is untyped
POST /v1/warehouse/migrate-statement-identity {"dry_run": true}  # read the plan
POST /v1/warehouse/migrate-statement-identity {"dry_run": false} # apply
```

Where a correctly-typed row already occupies the new id, the legacy row is left
alone rather than overwritten. Re-running is safe.

---

## Units

Aggregate money is stored in **INR million**. Vendors do not agree on magnitude
— Upstox reports crores, Yahoo reports absolute rupees, Capital IQ varies by
sheet — and conflict detection treats a gap above 2% as a disagreement. Crores
against rupees differ by 10,000,000%, so without a single canonical scale every
field on every row would register as a conflict and the conflict log would carry
no signal.

Normalisation happens in `units.py`, first in the gateway, before validation or
comparison sees a number.

### Unit classes are per column, not global

A share price and annual revenue are both `CURRENCY`, so the database type
cannot decide this. Each column declares a unit class:

| Class | Columns | Rescaled? |
|---|---|---|
| `inr_million` | revenue, EBITDA, PAT, assets, equity, debt, cash, capex, CFO/CFI/CFF | **yes** |
| `inr` | open/high/low/close, VWAP, dividend, EPS, book value | no |
| `count` | shares outstanding, volume | no |
| `ratio` / `percent` | multiples, delivery % | no |

Only `inr_million` columns are rescaled. Anything unclassified passes through
untouched, so forgetting to classify a column leaves it un-normalised rather
than corrupting it.

### Derived metrics cross the boundary

Market capitalisation is price times share count, so it is in rupees, while
statement aggregates are in millions. Anything mixing the two converts first
via `units.to_rupees` — book value per share, EPS from PAT, enterprise value,
EV/EBITDA, EV/Sales, price/sales. Without that step enterprise value would add
rupees to millions and every multiple would be out by a factor of a million.

### Rows written before normalisation

Each row records `sys_reported_unit`, `sys_unit_scale` and `sys_unit_method`,
surfaced as `reported_unit` in a row's `_meta`. A row with no stamp predates
this system, so its money columns are **skipped by conflict detection** — a gap
against an unstamped row would measure the vendor's magnitude rather than the
fact. Those deferrals are recorded in the audit log rather than passing silently.

```bash
GET  /v1/warehouse/unit-coverage                   # what is still unstamped
POST /v1/warehouse/normalise-units {"dry_run":true}  # read the plan
POST /v1/warehouse/normalise-units {"dry_run":false} # apply it
```

The migration groups by each row's own `source` so every vendor converts with
its own scale, and only touches rows with no stamp — running it twice cannot
double-scale a row.

---

## Daily refresh

```
18:45 IST → Groww → Yahoo → Capital IQ → NSE → CGL → Knowledge Factory
          → Financial Statements → Research → LIDI events
          → Validation → Recalculate → Publish
```

Each stage is independent: a dead collector degrades one stage and records the
error, it does not stall the run. Every run is written to `wh_refresh_runs` with
its stages, row counts and errors.

The scheduler thread lives in the gather worker (`scripts/gather_worker.py`), so
the HTTP process stays free for Ask. Groww is wired as a stage but reports
`no collector persisted yet` until a Groww collector writes to the warehouse.

---

## Access and audit

| Role | May |
|---|---|
| `read` | read every sheet, search, export |
| `edit` | + stage imports, edit cells, recalculate |
| `approve` | + commit imports, restore versions, clear overrides |
| `publish` | + publish, refresh, delete |

Every write names an actor; the browser stamps `X-AGI-Actor` on every request
and the Node proxy forwards it. Audited actions: import, edit, bulk_edit,
create, delete, override_clear, publish, refresh, recalculate, restore,
validate, export.

---

## Admin workspace

`/admin/data-warehouse` — a workbook with fourteen sheets.

- frozen header row, frozen filter row, sticky key column
- inline editing, range selection with Shift+arrows, keyboard navigation
- Ctrl/Cmd+C copy, Ctrl/Cmd+V multi-cell paste from Excel, Ctrl/Cmd+D fill down
- per-column filters, click-to-sort, drag-to-resize columns
- calculated columns visibly locked; overridden cells marked with a one-click
  revert to the imported value
- import dialog: paste or upload, auto column mapping you can correct, the
  validation report, then commit
- history drawer: cell changes, snapshots, diff, restore
- operations panel: data quality board, refresh runs, audit trail, run refresh
- global search across every sheet; CSV export of the current view

---

## Reading the warehouse from an engine

Intelligence modules should read the warehouse rather than the collectors:

```python
from institutional_warehouse.production import read_company, read_table

record = read_company("AXISBANK")   # master, valuation, ratios, consensus, factors, ...
rows = read_table("historical_valuation", limit=2000)
```

Ask reaches it through the KUL provider `institutional_warehouse`, which sits
ahead of the raw stores (valuation terminal, consensus, CapIQ, Knowledge
Factory) in every company-shaped plan while leaving each family's domain engine
in the lead. UKO registers it with `authority=warehouse`, `freshness=daily`.

---

## Running the tests

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest institutional_warehouse/tests -q

INSTITUTIONAL_WAREHOUSE_ROOT=/tmp/wh_acceptance PYTHONPATH=. \
  python3 scripts/warehouse_acceptance_v1.py
```

The acceptance suite builds a warehouse from the collectors on the machine and
checks the contract end to end: the fourteen tables, the refresh pipeline,
provenance, the override layer, server-owned calculations, versions and
restore, the audit trail, validation, Excel paste, global search, and the engine
read path.

---

## Known gaps

- **Groww** has no collector writing to the warehouse yet; the stage is wired
  and reports why it is idle.
- **FSE warehouse** facts are read when present, but the store is sparse today,
  so statements come mostly from Knowledge Factory and Capital IQ.
- **Beta** is reported as normalised volatility against a daily reference until
  an index series is warehoused; market-relative beta needs Nifty history in
  Daily Market History.
- **XLSX upload** is CSV/TSV today: save the sheet as CSV, or copy the cells and
  paste them.
- **Current and quick ratios** need `current_assets`, `current_liabilities` and
  `inventory`, which the current statement sources rarely carry.
