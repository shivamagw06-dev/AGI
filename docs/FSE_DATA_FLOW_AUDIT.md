# Financial Statements Data Flow Audit

### Version 1.0.0 · Pre-refactor baseline

| Field | Value |
| --- | --- |
| **Status** | Audit only — no code changes in this document |
| **Purpose** | Make FSE-02 the canonical ingestion layer without breaking downstream systems |
| **Scope** | Collectors · storage · writers · readers · events · duplicate pipelines · migration plan |
| **Workspace evidence date** | 2026-07-30 |

> **Verdict:** AGIB currently has **two parallel financial-statement data planes**. Historical Depth (HD) is the *de facto* production store fed by `earnings_intelligence`, `FinancialStatementsConnector`, Yahoo, and fixtures. FSE-02→Parse→Validate→Warehouse→DME is the *designed* canonical plane but is largely empty and not wired into CGL.

---

# 1. All collectors (writers of statement-related data)

| # | Collector | Fetches | Writes to | Format | Production role today |
| --- | --- | --- | --- | --- | --- |
| A | **`earnings_intelligence`** (`discovery` → `xbrl` → `pack` → `store.persist_pack`) | NSE filing discovery + XBRL download/parse | `KF_HD_STORE_ROOT/financials_annual\|quarterly/{TICKER}.json` | HD PIT records; `source=earnings_intelligence_p21`; flattened revenue/ebit/ni/… in `payload` | **Primary live writer** (~20 tickers) |
| B | **`FinancialStatementsConnector`** (`institutional_data/connectors/financials.py`) | NSE via EI primary; Yahoo `quoteSummary` failover | Same HD series via `put_series`; `source=financial_connector` (when stored through connector path) | Connector records → HD PIT | Invoked by institutional/CGL backfill |
| C | **HD collectors** (`knowledge_factory/historical_depth/collectors/__init__.py`) | Orchestrates live + fixture seed | HD `financials_*` | PIT series | Batch collector entry |
| D | **Yahoo live** (`collectors/yahoo_live.py`) | Yahoo chart (prices/actions) + **thin annual close proxies** | HD `prices`, `corporate_actions`, **and `financials_annual`** (price-derived, non-canonical) | PIT; not true statements | Live when `KF_HD_LIVE_COLLECTORS=true` |
| E | **HD fixtures** (`fixtures/seed_history.py`) | Synthetic history | HD `financials_*` | PIT; `source=fixture` | **Blocked in prod** for new writes; residual ~88% of on-disk records |
| F | **FSE-02 collection** (`financial_statements_engine/collection/`) | NSE/BSE/IR discovery adapters → download bytes | `FSE_STORE_ROOT/raw/{TICKER}/` + `raw_meta/` | Immutable raw bytes + metadata; emits `evidence.stored` | **Code-complete; store empty; not on CGL** |
| G | **FSE-01 `ingest_and_publish`** (`production.py`) | Soft-wraps EI pack | Legacy `published/` + `warehouse.publish_statement` | Canonical statement packs (pre-FWH) | Migration/legacy path; bypasses FSE-02 raw |
| H | **LIDI Company IR** | IR HTML/PDF catalogues | `LIDI_STORE_ROOT` objects | Document objects, not HD financials | Statement-*adjacent*; not a FS series writer |

### Per-collector detail

#### A. `earnings_intelligence`
- **Fetch:** NSE APIs (`discover_filings`) → XBRL URL → parse (`xbrl.py`) → `build_financial_pack`
- **Write:** `persist_pack` → `hd_store.put_series("financials_quarterly"|"financials_annual")`
- **Consumers of its output:** HD completion, CGL heat maps, company_memory financial derive, sector producers, ECD (reads HD for filing presence)
- **Does not write:** FSE raw, FWH facts, DME

#### B. `FinancialStatementsConnector`
- **Fetch:** `_nse_financials` (EI) then Yahoo statement modules
- **Write:** `store()` → `put_series` annual/quarterly
- **Fixtures:** `fixtures_allowed()` false when `APP_ENV=production`
- **Consumers:** same HD readers as A

#### D. Yahoo live (important contamination risk)
- Writes **price-proxy annuals** into `financials_annual` — not IND-AS statements
- Must not be treated as canonical financial facts during migration

#### F. FSE-02
- **Fetch:** adapters `nse` / `bse` / `ir` → `downloader.download_bytes`
- **Write:** `collection.writer.write_evidence` → `raw_evidence.store_raw`
- **Stops at raw.** Explicitly `parses_financials: false`, `writes_warehouse: false`
- **Intended consumers:** Parse subscriber on `evidence.stored` → drafts → VFQE → FWH → DME

---

# 2. All storage locations

```text
LIVE SOURCES: NSE XBRL · BSE · IR · Yahoo failover
        │                           │
        ▼                           ▼
earnings_intelligence          FSE-02 collection
FinancialStatementsConnector   (intended canonical)
Yahoo live / fixtures                 │
        │                             ▼
        ▼                      FSE RAW (empty today)
HD STORE (active SoR)          data/raw/{TICKER}/
financials_annual/                    │ evidence.stored
financials_quarterly/                 ▼
(~110 tickers; ~88% fixture)   Parse → Validate → FWH → DME
        │
        └──► company_memory / CGL / KF completion / ECD
```

| Store | Root env / default | Contents | Populated? |
| --- | --- | --- | --- |
| HD financials | `KF_HD_STORE_ROOT` → `…/knowledge_factory/historical` | PIT annual/quarterly series | **Yes** (fixture-heavy) |
| FSE raw | `FSE_STORE_ROOT` (unset in `render.yaml`) → `financial_statements_engine/data` | Raw filing bytes | **Empty (0 files)** |
| FSE drafts / ECM | under FSE store `parsing/` | Canonical drafts, coverage matrices | Empty in prod corpus |
| FSE validation | `validation/reports/` | VFQE reports | Empty |
| FWH | `warehouse/facts/` | Validated facts | Empty outside tests |
| DME | `derived_metrics/metrics/` | Derived metric versions | Empty outside tests |
| Legacy published | `published/`, `derived/` | FSE-01 packs | Sparse / legacy |
| LIDI | `LIDI_STORE_ROOT` | IR docs | Not FS series |

**Duplicate paths:** HD `financials_*` vs FSE raw→warehouse are parallel SoRs for “company financials.”

---

# 3. All writers (symbol-level)

| Writer function | Module | Target |
| --- | --- | --- |
| `persist_pack` | `earnings_intelligence/store.py` | HD `financials_*` |
| `FinancialStatementsConnector.store` → `put_series` | `institutional_data/connectors/financials.py` | HD `financials_*` |
| `collect_entity_history` / fixture seed | `historical_depth/collectors`, `fixtures/seed_history.py` | HD `financials_*` |
| `collect_entity_live` annual proxy | `collectors/yahoo_live.py` | HD `financials_annual` (proxy) |
| `write_evidence` / `store_raw` | `collection/writer.py`, `raw_evidence.py` | FSE raw |
| `publish_statement` | `warehouse.py` (legacy) | FSE published packs |
| `publish_validated_pack` | `financial_warehouse/publisher/publish.py` | FWH facts |
| `persist_calculation` / `store_metric` | `derived_metrics/publication/persist.py` | DME store |

---

# 4. All readers (consumers)

| Consumer | Reads from | Notes |
| --- | --- | --- |
| HD `completion` / `company_scorecard` | HD `financials_*` | Hard gate `financial_statements` |
| CGL `ops_observability.coverage_heat_map` | HD | Dataset heat map |
| `company_memory/derive/financial.py` | HD annual | Memory / research features |
| KF sector / objects / time_travel | HD | Intelligence producers |
| FSE-ECD dashboard | HD (filing presence) + FSE stages | Funnel measurement |
| FSE Parser | FSE raw bytes (via `evidence.stored` subscriber) | Only if subscriber bound |
| VFQE | Canonical drafts | Not HD |
| FWH contracts (`dcf.v1`…) | FWH facts | Designed consumer surface |
| DME | FWH `get_latest` only | Must not read HD |
| Ask / Research Notes (intended) | Should use FWH/DME contracts | Today many paths still HD-backed |

**Breakage risk if HD writes stop before FWH is populated:** completion gates, CGL heat maps, company_memory financial derive, ECD “latest filing” stage, any research path still on HD.

---

# 5. Event flow

### Catalogue (`financial_statements_engine/events.py`)

| Stage | Events |
| --- | --- |
| Collection | `discovery.filing_found/updated`, `evidence.stored`, `evidence.duplicate_skipped`, `evidence.restatement_candidate`, `collection.job_failed/completed` |
| Parse | `parse.*.v1`, `draft.created/updated.v1`, … |
| Coverage / PCC | `coverage.*.v1`, `pcc.*.v1` |
| Validation | `validation.{started,completed,approved,rejected,quarantined}.v1` |
| Warehouse | `warehouse.facts_published.v1`, `warehouse.publish_rejected.v1` |
| DME | `derived_metrics.{calculated,published,calculation_failed,restatement_recalculated}.v1` |

### Emitters (production code)

| Event | Emitted by |
| --- | --- |
| `discovery.filing_*` | `collection/discovery.py` |
| `evidence.stored` (+ dup/restatement) | `collection/pipeline.py` |
| `parse.completed.v1` / drafts | `parsing/pipeline.py` |
| `validation.*.v1` | `validation/pipeline.py` |
| `warehouse.facts_published.v1` | `financial_warehouse/publisher/publish.py` |
| `derived_metrics.*.v1` | DME persist / restatement |

### Subscribers (production)

| Event | Subscriber | Bound when |
| --- | --- | --- |
| `evidence.stored` | `parsing/subscriber.on_evidence_stored` → `parse_document` | Only when `parsing.production.health()` calls `bind_evidence_subscriber()` — **not** app lifespan |
| All later stages | **No durable subscribers** chaining parse→validate→warehouse→DME | Manual / API |

### Emitted but not chained into an automatic pipeline

```text
evidence.stored ──(optional soft parse)──► draft
parse.completed.v1          ✗ no validate subscriber
validation.approved.v1      ✗ publish is in-process when validate API runs with publish=True
warehouse.facts_published.v1 ✗ no DME subscriber (DME only hooks restatement path)
derived_metrics.published.v1 ✗ no Ask/Research auto-consumer
```

HD / EI / connector writes emit **no FSE bus events**.

---

# 6. Duplicate pipelines

| Pipeline | Path | Status |
| --- | --- | --- |
| **P1 — HD live/fixture plane** | NSE/Yahoo → EI/Connector/Yahoo/fixtures → HD `financials_*` → KF/CGL/company_memory | **Active SoR** |
| **P2 — FSE canonical plane** | Discover→Download→FSE raw→Parse→Validate→FWH→DME | **Designed; raw empty; not scheduled** |
| **P3 — FSE-01 legacy ingest** | EI pack → `ingest_and_publish` → legacy published | Soft migration helper |
| **P4 — Yahoo proxy annuals** | Chart closes → `financials_annual` | Contaminates HD statement series |

This is why ECD shows HD filing presence without FSE parse/validate/publish/DME progress.

---

# 7. Recommended migration plan (no code yet — sequence only)

## Goal

```text
All official filing bytes enter via FSE-02 Raw Evidence Store.
HD financials become a derived projection (or temporary dual-write),
not an independent ingestion SoR.
Parse → Validate → Warehouse → DME become the only path to
canonical facts and ratios.
```

## Phase 0 — Freeze assumptions (this audit)

- Treat HD as **read-compatible legacy** during cutover.
- Do not delete HD series until FWH+DME cover gold → Nifty50 → Nifty500.
- Mark Yahoo proxy annuals as non-canonical (filter in readers).

## Phase 1 — Make FSE-02 the only *byte* ingestion path

**Redirect (do not rewrite parsers yet):**

| Module | Change |
| --- | --- |
| `earnings_intelligence` | After XBRL download, **also** (then eventually **only**) call FSE-02 `write_evidence` with raw bytes + metadata; keep HD persist behind feature flag |
| `FinancialStatementsConnector` | Stop writing HD directly from Yahoo/NSE parsed packs as SoR; for NSE, hand raw bytes to FSE-02; Yahoo statements = failover projection only |
| FSE-02 adapters | Become the sole discovery/download orchestration used by CGL |
| CGL / HD backfill | Schedule FSE-02 collect jobs for missing filings (gap-driven) |

**Retire later:** Yahoo → `financials_annual` proxy writes; fixture seed for financials.

## Phase 2 — Wire the automatic FSE chain

```text
evidence.stored
  → parse (bind at app lifespan)
  → validation.approved
  → warehouse.facts_published
  → derived_metrics.calculate/persist
```

Durable subscribers (or an orchestrator worker) — not on-demand health() binding.

## Phase 3 — Dual-read / dual-write window

- **Write:** FSE-02 raw + (temporary) HD projection from warehouse/DME or from approved packs
- **Read:**
  - DME / Ask / contracts → FWH/DME only
  - HD completion → accept FWH presence **or** HD until coverage threshold met
- ECD becomes the cutover scoreboard (all funnel stages → 100%)

## Phase 4 — Retire bypass writers

1. Disable EI `persist_pack` HD writes (flag off)
2. Disable connector HD statement `put_series` for canonical path
3. Disable Yahoo proxy annuals into `financials_annual`
4. Keep HD series as read-only archive / projection rebuilt from FWH if needed

## Phase 5 — Backfill

- For each Nifty500 company: discover historical filings via FSE-02 → store raw → replay parse/validate/publish/DME
- Prefer coverage-before-depth (latest annual/quarter first)
- Do not trust fixture HD rows as raw evidence

---

# 8. What can be retired vs redirected

| Component | Action |
| --- | --- |
| FSE-02 collection | **Promote** to sole byte SoR; attach to CGL |
| EI discovery + XBRL download | **Redirect** raw bytes into FSE-02; keep as adapter implementation |
| EI `persist_pack` → HD | **Deprecate** after dual-write window |
| `FinancialStatementsConnector` HD store | **Deprecate** as SoR; become FSE-02 client + Yahoo failover projection |
| Yahoo `financials_annual` proxies | **Retire** from statement series (move to prices-derived analytics if needed) |
| HD fixtures for financials | **Retire** (already blocked for new prod writes) |
| FSE-01 `ingest_and_publish` | **Retire** once FSE-02 chain covers gold |
| HD `financials_*` readers | **Migrate** to FWH/DME contracts over time; keep shim during cutover |
| Parse subscriber | **Harden** — bind at app start; add validate/warehouse/DME chain |

---

# 9. Transition without breaking downstream

| Risk | Mitigation |
| --- | --- |
| HD completion goes red | Dual-write HD from approved FWH packs during Phase 3; or completion reads FWH |
| company_memory empty | Temporary adapter: prefer FWH, fallback HD |
| CGL heat map drops | Project FWH period counts into heat-map inputs |
| Research notes lose series | Point to `ask_agib.v1` / `ask_agib_metrics.v1` contracts |
| Empty FSE raw blocks parse | Phase 1 must populate raw **before** disabling HD writers |
| Yahoo rate limits | Keep as failover only; do not scale Yahoo as primary SoR |

**Hard rule during migration:** never invent financial facts; never let consumers calculate ratios outside DME; never treat Yahoo price proxies as validated statements.

---

# 10. Success criteria for “FSE-02 is canonical”

1. Every new official filing byte is present under FSE raw (idempotent).
2. No production path writes `financials_*` except an approved FWH→HD projector (if retained).
3. `evidence.stored` always triggers parse→validate→(on approve) warehouse→DME without manual API calls.
4. ECD Nifty500: latest annual/quarterly **and** parsed/validated/published/derived climb together — not HD-only.
5. `render.yaml` defines `FSE_STORE_ROOT` on durable disk.

---

# Appendix A — Package trees (audit snapshot)

### `financial_statements_engine` (L3, abbreviated)

`collection/` (adapters, pipeline, writer, event_bus, scheduler) · `parsing/` (pipeline, subscriber, coverage, pcc, quality) · `validation/` · `financial_warehouse/` · `derived_metrics/` · `evidence_coverage/` · `data/{raw,raw_meta,warehouse,derived_metrics,…}` · `extraction/` · `events.py` · `raw_evidence.py` · `production.py`

### `institutional_data` (L3)

`connectors/{financials,bse,ir_discovery,…}` · `backfill/chunked.py` · `persistence/` · `production.py`

### `earnings_intelligence` (L3)

`discovery.py` · `xbrl.py` · `pack.py` · `store.py` · `production.py` · `analytics.py` · `enrich.py`

### HD collectors

`historical_depth/collectors/{__init__.py,yahoo_live.py}` · `fixtures/seed_history.py` · `store.py` · `backfill.py` · `completion.py`

---

# Appendix B — Grep anchors

| Pattern | Key hits |
| --- | --- |
| `put_series("financials_` | `earnings_intelligence/store.py`, `connectors/financials.py`, `collectors/__init__.py`, `yahoo_live.py` |
| `write_evidence` / `store_raw` | `collection/writer.py`, `raw_evidence.py`, FSE-02 pipeline |
| `evidence.stored` | Emitted: `collection/pipeline.py`; Consumed: `parsing/subscriber.py` |
| `publish_validated_pack` | VFQE publish → FWH; restatement engine |
| `financials_annual` readers | `completion.py`, `ops_observability.py`, `company_memory/derive/financial.py`, ECD stages |

---

**Next step after acceptance of this audit:** implement Phase 1 only (FSE-02 as sole byte ingestion + dual-write flag), measured by ECD raw/filing stages — not a full parser rewrite.
