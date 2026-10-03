# AGIB Knowledge Source Audit

**Role:** Chief Data & Knowledge Architect  
**Type:** Code-truth platform audit (not investment advice)  
**Scope:** Implemented behaviour in the repository only  
**Labels used:** `LIVE` · `FIXTURE` · `SEED` · `DERIVED` · `NOT IMPLEMENTED` · `LICENSE REQUIRED` · `UNKNOWN` · `NOT CONFIGURED`

**Hard rule:** Never invent sources. If the code does not fetch it, it is not live.

---

## Executive verdict

Almost all AGIB knowledge is **SEED / FIXTURE / DERIVED**, not live official feeds.

| Class | Reality in code |
| --- | --- |
| Truly live market ingestion | **None for institutional payloads.** Yahoo optional `KF_LIVE_YAHOO` only probes `query1.finance.yahoo.com` connectivity; **payload remains fixture** (`primitive_panel` / `price_series`). |
| Track-1 collectors (Yahoo/NSE/BSE/Groww/RBI/FRED/WB) | Default **FIXTURE**; NSE/Groww live flags return `*_live_not_configured`. |
| ICI / ICEI / IGRI / IIVI / IERI / IADI / IMEI | **SEED** corpora + soft-reads; in-memory stores for most soft layers. |
| Licensed street consensus | **LICENSE REQUIRED / NOT CONFIGURED** → all consensus fields `UNKNOWN`. |
| PMI manufacturing | **LICENSE REQUIRED** (Phase 2 shell); Phase 1 uses public IIP seed instead. |

**Overall source maturity score: 3.5 / 10**  
Strong institutional *schema and provenance design*; weak *live Indian-market ingestion*.

---

# 1. Universe Intelligence

| Field | Code-truth |
| --- | --- |
| **Purpose** | Maintain investable universes, membership, coverage scores (IUI). |
| **Data sources** | Seed registries from `institutional_reasoning.fundamentals.nifty500_universe` + `universe_intelligence/fixtures/seed_universes.py`. |
| **Collectors** | Bootstrap / pipeline — not NSE live index APIs. |
| **Validators** | Universe quality gates / coverage modules. |
| **Derived producers** | Company compile, membership `was_member` / `members_as_of`, incremental apply. |
| **Stored objects** | Universes, snapshots, membership, companies under `IUI_STORE_ROOT` or `{kf_parent}/universe_intelligence/`. |
| **Evidence packs** | Universe coverage / ICI aggregates (dashboard), not Track-1 PE packs. |
| **Update frequency** | Morning DAG `universe_update` (schedule metadata `06:00`). |
| **Historical coverage** | Fixture reconstitution events only (e.g. ZOMATO, TRENT, YESBANK, PERSISTENT, INDIGO). |
| **Point-in-time** | `members_as_of` / membership events supported in code. |
| **Provenance** | `source`, `retrieved_at`, `validated_at`, `confidence`, `collector`, `fabricated: false`. |
| **Confidence** | Seed confidence; reconstitution tagged `fixture_reconstitution`. |
| **APIs** | `/v1/universe-intelligence/*`, IKS dashboard soft-read. |
| **Morning workflow** | Handler → `run_universe_intelligence_pipeline(universe_id="NIFTY_500")`. |
| **Status** | **SEED** operational; **live NSE reconstitution NOT IMPLEMENTED**. |

### Constituents

| Universe | Status | Source |
| --- | --- | --- |
| Nifty 50 | Implemented (seed) | Hardcoded / IR fundamentals seed |
| Nifty 100 | Implemented (seed) | N50 + extras |
| Nifty 500 | Implemented (seed) | `NIFTY_500` registry (~500 members) |
| Nifty IT | Implemented (thematic seed) | Hardcoded thematic list |
| Nifty 1000 | Declared shell | Members copy N500 — coverage not claimed |
| Global (SPX/NDX/…) | Declared / deferred stubs | Empty or shell |
| Registry | Yes | Seed registries + company compile |
| Membership history | Partial | Fixture membership events |
| Reconstitution | Fixture only | **NOT IMPLEMENTED** as live NSE feed |

---

# 2. Company Intelligence (ICI + Track-1 company objects)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Per-company institutional object + Track-1 valuation/accounting/risk objects. |
| **Data sources** | Soft-reads: Nifty sector map, Sector DNA, `company_analysis` priors, management packs, KF company objects; deep **SEED** for INFY, TCS, HDFCBANK, NESTLEIND. |
| **Collectors** | Track-1: `collectors/yahoo`, `nse`, `bse` (fixture). ICI: `collectors/soft.py` — no live scrape of ARs/MCA. |
| **Validators** | Track-1 `validate_dataset`; ICI field validators / UNKNOWN gates. |
| **Derived producers** | `produce_valuation`, `produce_accounting`, `produce_business_quality`, `produce_risk`, `produce_peers`, `produce_timeline`; ICI `produce_all_modules`. |
| **Stored objects** | Track-1 file store `objects/company/{ENTITY}.json`; ICI **in-memory** store. |
| **Evidence packs** | Track-1 `packs/{ENTITY}.json` (PE, risk_drivers, coverage…). |
| **Update frequency** | Track-1 `run_daily`; morning `company_intelligence` + `evidence_pack_generation`. |
| **Historical coverage** | Via Historical Depth soft-read / HD packs when run. |
| **Point-in-time** | HD packs claim PIT; ICI qualitative mostly current seed. |
| **Provenance** | Field-level; unavailable → `source: unavailable`, confidence 0. |
| **APIs** | `/v1/company-intelligence`, KF company APIs, IKS `company/{ticker}`, Ask soft packs. |
| **Morning** | `run_company_intelligence_pipeline` over Nifty 500. |
| **Status** | **SEED + FIXTURE + DERIVED**. Live filings/MCA/AR scrape **NOT IMPLEMENTED**. |

### Field → source map (code-truth)

| Field | Source in code |
| --- | --- |
| Company profile / business narrative | ICI seed (4 names) or **UNKNOWN** |
| Sector | `NIFTY_500_SECTOR` / `sector_map()` seed |
| Industry | Industry map / playbook soft-read |
| Exchange | Fixture tags (NSE/BSE on filings seed) |
| Financial statements | Track-1 primitives from **fixture panel** (not live XBRL) |
| Ownership / shareholding | **NOT IMPLEMENTED** as live CDSL/NSDL/SHP feed → typically **UNKNOWN** |
| Risk | **DERIVED** `produce_risk` / IR fundamentals |
| Valuation | **DERIVED** from fixture primitives + IR derivations |
| Historical valuation | Historical Depth **FIXTURE** series (FY07–FY26 design) |
| Timeline | Filings fixture + ICEI seeds / HD timeline |
| Accounting | **DERIVED** accounting metrics |
| Business quality | **DERIVED** from ROIC/valuation |

---

# 3. Historical Intelligence

| Field | Code-truth |
| --- | --- |
| **Purpose** | Deep history for replay / coverage (Historical Depth). |
| **Data sources** | `historical_depth/fixtures/seed_history.py` — `source="fixture"`. |
| **Collectors** | `collect_entity_history`, `collect_market_history`, `collect_universe`. |
| **Validators** | HD validation path in pipeline. |
| **Derived producers** | `produce_derived` → company/macro/sector HD objects. |
| **Stored objects** | Under `KF_HD_STORE_ROOT` or `{engine}/data/knowledge_factory/historical/` (`prices/`, `financials_*`, `corporate_actions/`, `timeline/`, `regimes/`, `macro/`, `packs/`). |
| **Evidence packs** | HD packs per entity. |
| **Update frequency** | Morning `historical_update` → `run_daily_pipeline(historical_depth=True)` or HD pipeline fallback. |
| **Historical coverage** | Designed **FY07–FY26 (~20 years)**; monthly prices ~2007-04→2026-03; rich panels INFY/HDFCBANK, others parametric. |
| **Point-in-time** | Explicit PIT fields (`available_from`, immutable). |
| **Provenance** | Fixture provenance + PIT metadata. |
| **Confidence** | Fixture confidence; not market-vendor certified. |
| **APIs** | KF historical-depth routes; Ask/Research soft-read. |
| **Morning** | Level after universe. |
| **Status** | **FIXTURE**. Live exchange history **NOT IMPLEMENTED**. |

| Slice | Status |
| --- | --- |
| Historical financials | FIXTURE |
| Historical valuation | FIXTURE / DERIVED |
| Historical replay | FIXTURE + Research Office / IDQ replay ids |
| Historical timelines | FIXTURE + ICEI seeds |
| Historical macro | FIXTURE annual series |
| Historical sector history | FIXTURE / sector compile |
| Years of history | ~20y in seed design |

---

# 4. Corporate Event Intelligence (ICEI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Company event timelines. |
| **Data sources** | Curated event seeds (INFY, TCS, HDFCBANK, NESTLEIND) + soft ICI/HD timelines. Declared priority: NSE/BSE filings, ARs, SEBI, MCA — **not live scraped**. |
| **Collectors** | `collect_event_context` (soft). |
| **Validators** | Event validation gates. |
| **Derived producers** | `compile_company_timeline`. |
| **Stored objects** | In-memory ICEI store. |
| **Evidence packs** | Timeline soft-feed into `evidence_feed` / company bundle. |
| **Update frequency** | Morning `corporate_events`. |
| **Historical coverage** | Seed events + HD corporate_actions fixture. |
| **Point-in-time** | Event dates on seeds; full exchange PIT **NOT IMPLEMENTED**. |
| **Provenance** | Per-event provenance objects. |
| **APIs** | `/v1/corporate-events`, IKS company bundle. |
| **Morning** | After company intelligence. |
| **Status** | **SEED**. Live NSE announcements / BSE corp actions **NOT IMPLEMENTED**. |

| Event type | Implemented as |
| --- | --- |
| Results / guidance | Seed / soft expectations |
| Dividends / buybacks / splits | Seed / filings fixture types |
| CEO changes / acquisitions | Seed for core names |
| Litigation / contracts / regulatory | Seed where present; else **UNKNOWN** |

---

# 5. Government Intelligence (IGRI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Policy knowledge for RBI/Budget/SEBI/GST/PLI/Trade (Phase 1). |
| **Data sources** | **SEED** policy corpus (`fixtures` / seeds) with tags like `rbi`, `ministry_of_finance`, SEBI evidence ids — curated, **not scraped**. |
| **Collectors** | `collect_government_context`. |
| **Validators** | Policy validation; `political_opinion: false`, `policy_forecast: false`. |
| **Derived producers** | Policy compile / dashboard. |
| **Stored objects** | In-memory. |
| **Evidence packs** | Soft into company `evidence_feed` when companies listed as affected. |
| **Update frequency** | Morning `government_intelligence` (parallel-ok with company). |
| **Historical coverage** | Seed policies spanning selected years (e.g. GST launch, budgets 2020/23/24). |
| **Point-in-time** | Policy effective dates in seeds; live gazette feed **NOT IMPLEMENTED**. |
| **Provenance** | Per-policy provenance. |
| **APIs** | `/v1/government`, Research Office government brief soft-read. |
| **Morning** | Yes. |
| **Status** | Phase 1 **SEED**. Live RBI DBIE / SEBI / GSTN / gazette **NOT IMPLEMENTED**. Phase 2 domains (MCA, state, …) extensible empty. |

| Domain | Status |
| --- | --- |
| RBI | SEED |
| SEBI | SEED |
| Budget | SEED |
| GST | SEED |
| PLI | SEED |
| Import/Export duties / Trade | SEED (trade/FTP/customs corpus) |
| Live RBI/SEBI/GSTN APIs | **NOT IMPLEMENTED** |

---

# 6. Industry Intelligence (IIVI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Industry playbooks, value-chain maps, company→industry mapping. |
| **Data sources** | Curated playbooks (`playbooks/catalog.py`) + Sector DNA soft-read + IGRI domain refs. **Not** association APIs. |
| **Collectors** | `collect_industry_context`. |
| **Validators** | Industry object gates. |
| **Derived producers** | `compile_all_industries`, company industry map for N500. |
| **Stored objects** | In-memory. |
| **Evidence packs** | Soft industry pack in Ask / Research Office. |
| **Update frequency** | Morning `industry_intelligence`. |
| **Historical coverage** | Playbook qualitative; not multi-decade industry stats feeds. |
| **Point-in-time** | Limited. |
| **Provenance** | Playbook / soft prior tags. |
| **APIs** | `/v1/industry`. |
| **Morning** | After company. |
| **Status** | **SEED**. Rich playbooks for ~18 deep industries; others template/**UNKNOWN**. Live industry feeds **NOT IMPLEMENTED**. |

| Concept | Status |
| --- | --- |
| Industry playbooks | SEED (deep set) |
| Business models / accounting / valuation rules | SEED in playbooks |
| Industry KPIs | SEED / UNKNOWN by industry |
| Value / supply chains | SEED + soft priors |
| Industry cycles | Descriptive seed / UNKNOWN |

---

# 7. Economic Relationship Intelligence (IERI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Structural / financial / policy / market / operational / behavioural edges. |
| **How obtained** | (1) `curated_relationship_seeds()` (2) `soft_relationships_from_priors()` from IIVI value-chain, IGRI policy links, `TICKER_PEERS`. **Never invent** missing edges. |
| **Collectors** | Soft collectors in package. |
| **Validators** | `validate_relationship`. |
| **Derived producers** | `build_relationship`, pipeline compile. |
| **Stored objects** | In-memory. |
| **Evidence packs** | Relationship soft packs. |
| **Update frequency** | Morning `economic_relationships`. |
| **Historical coverage** | Seed edges; not time-varying live graphs. |
| **Point-in-time** | Limited. |
| **Provenance** | Evidence tags e.g. `sector_dna_oil_sensitivity_public`, `annual_reports` (as tags, not scraped docs). |
| **APIs** | `/v1/relationship`. |
| **Morning** | After industry. |
| **Status** | **SEED + soft priors**. Live supplier/customer filings graph **NOT IMPLEMENTED**. |

| Relationship class | How obtained |
| --- | --- |
| Supplier / customer | Soft value-chain priors / seeds — **not** invoice networks |
| Competitors | `TICKER_PEERS` / seed competitor edges |
| Commodity exposure | Curated sensitivity seeds |
| Government / macro / financial / behavioural | Seed + IGRI/IIVI soft links |

---

# 8. Alternative Data Intelligence (IADI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | High-signal real-economy observations preceding earnings (knowledge only). |
| **Data sources** | Phase-1 **SEED** series (`live_scrape: False`), monthly, ~2019-01→2024-12, deterministic synthetic indexes. |
| **Collectors** | `collect_phase1_bundle` / curated observation series. |
| **Validators** | Dataset gates. |
| **Derived producers** | `compile_alternative_data`, momentum/coverage dashboards. |
| **Stored objects** | In-memory datasets + observations. |
| **Evidence packs** | Soft alt-data packs. |
| **Update frequency** | Morning `alternative_data` (failure isolated). Registry frequency: **monthly**. |
| **Historical depth** | ~6 years seed (2019–2024). |
| **Point-in-time** | Observation `as_of` lists. |
| **Provenance** | Provider tags (NPCI, POSOCO, MOSPI, …) on registry — **not live pulled**. |
| **APIs** | `/v1/alternative-data`. |
| **Morning** | After relationships. |
| **Status** | Phase 1 **SEED**. Live NPCI/Grid/MOSPI/… **NOT IMPLEMENTED**. |

### Phase-1 datasets (implemented as curated seeds)

| Dataset | Registry provider | Official (declared) | Collector status | Frequency | Historical depth |
| --- | --- | --- | --- | --- | --- |
| UPI transactions | NPCI | NPCI | SEED | monthly | ~2019–2024 seed |
| Electricity demand | Grid India / POSOCO | POSOCO | SEED | monthly | ~2019–2024 seed |
| IIP manufacturing | MOSPI | MOSPI | SEED (PMI substitute) | monthly | ~2019–2024 seed |
| Railway freight | Indian Railways | IR | SEED | monthly | ~2019–2024 seed |
| Port cargo | Mo Ports / IPA | MoP | SEED | monthly | ~2019–2024 seed |
| Vehicle registrations | VAHAN / MoRTH | VAHAN | SEED | monthly | ~2019–2024 seed |
| Air passengers domestic | DGCA | DGCA | SEED | monthly | ~2019–2024 seed |
| Bank credit growth | RBI | RBI | SEED | monthly | ~2019–2024 seed |
| Rainfall monsoon | IMD | IMD | SEED | monthly | ~2019–2024 seed |
| GST collections | GSTN / MoF | GSTN | SEED | monthly | ~2019–2024 seed |

### Phase-2 shells (**NOT IMPLEMENTED**)

`neft_rtgs_imps`, `fastag_toll`, `cement_dispatch`, `steel_production`, **`pmi_manufacturing` → LICENSE REQUIRED (S&P Global)**, `housing_sales`, `wireless_subscribers`, `trade_balance`, `coal_stocks`, `metro_ridership`.

---

# 9. Market Expectations Intelligence (IMEI)

| Field | Code-truth |
| --- | --- |
| **Purpose** | Guidance / actuals / AGIB forecasts / revisions / surprises / narratives; reality vs expectations. |
| **Phase 1 sources** | SEED: `company_guidance`, `company_earnings_release`, `exchange_disclosure`, `investor_presentation`, `agib_internal_forecast`. |
| **Phase 2 consensus** | Modular collector `collect_licensed_consensus`. |
| **Collectors** | Phase-1 seed collector; licensed consensus collector. |
| **Validators** | Expectation validation / revision / surprise producers. |
| **Derived producers** | Revisions, surprises, gaps, narratives. |
| **Stored objects** | In-memory expectations store. |
| **Evidence packs** | Soft expectation packs + gaps. |
| **Update frequency** | Morning `market_expectations`. |
| **Historical coverage** | Seed expectation history for core names. |
| **Point-in-time** | Period fields on expectations. |
| **Provenance** | Source tags; `licensed_consensus: false` in Phase 1. |
| **APIs** | `/v1/expectations`, phase2-consensus status route. |
| **Morning** | After alt-data (soft dep). |
| **Status** | Phase 1 **SEED**. Street consensus **LICENSE REQUIRED**. |

### If licensed consensus is NOT configured

```text
AGIB_LICENSED_CONSENSUS_PROVIDER unset
  → status: not_configured
  → consensus.median/mean/high/low/std_dev/n_estimates = UNKNOWN
  → licensed_consensus: false
  → fabricated: false
  → Phase-1 guidance/actuals/AGIB forecast seeds still run
```

If env is set but adapter pending → `provider_configured_adapter_pending` and consensus fields remain **UNKNOWN**. **Never scrapes broker reports.**

| Object | Status |
| --- | --- |
| Company guidance | SEED |
| Reported results | SEED |
| Expectation history | SEED |
| AGIB forecasts | SEED (`agib_internal_forecast`) |
| Revisions / surprises / narratives | DERIVED from seeds |
| Licensed street consensus | **LICENSE REQUIRED / NOT CONFIGURED → UNKNOWN** |

---

# 10. Evidence Factory

| Field | Code-truth |
| --- | --- |
| **Purpose** | Bind knowledge into packs for governance / Ask / Research Office. |
| **Track-1 packs** | Built in `run_daily` → `store.put_pack` from valuation/risk/coverage. |
| **Soft feeds** | `knowledge_factory.production.evidence_feed(entity)` aggregates company object, pack, HD, ICI, ICEI, IGRI, IIVI, IERI, IADI, IMEI soft-reads. |
| **Ask Evidence Assembly** | `ask_pipeline.evidence.assemble_evidence` builds envelopes from KF bag. |
| **Validators** | Track-1 validation before publish; Ask gates on provenance. |
| **Update frequency** | Morning `evidence_pack_generation` + Ask-time assembly. |
| **Status** | **OPERATIONAL as soft aggregation**; richness limited by seed/fixture upstream. |

| Pack | Feeds from (implemented) |
| --- | --- |
| Company Pack | Track-1 company object + pack + ICI soft |
| Industry Pack | IIVI soft |
| Government Pack | IGRI soft |
| Alternative Data Pack | IADI soft |
| Relationship Pack | IERI soft |
| Expectation Pack | IMEI soft |
| Portfolio Pack | Groww book fixture → portfolio object (when present) |
| Decision Pack | Ask pipeline decision envelope (metadata) |

---

# 11. Morning Scheduler (06:00 DAG)

**Schedule string in code:** `06:00` (`dag_id: morning_operations_0600`).  
**In-repo cron daemon:** **NOT IMPLEMENTED** — callable via `POST /v1/scheduler/run` / `run_morning()`.

### Execution DAG (implemented levels)

```text
universe_update
  → historical_update
  → company_intelligence ‖ government_intelligence
  → corporate_events
  → industry_intelligence
  → economic_relationships
  → alternative_data
  → market_expectations
  → evidence_pack_generation
  → coverage_validation
  → quality_gates
  → mission_control ‖ daily_health
  → research_queue
  → morning_reports
  → ready_declaration
  → [soft] research_office if system_ready
```

| Concern | What runs |
| --- | --- |
| Collectors | Track-1 fixture collectors inside `run_daily` / HD; soft-layer pipelines bootstrap seeds |
| Datasets refresh | Seed/fixture recompile into stores; not live official pulls |
| Validations | KF validate_dataset; layer gates; scheduler morning quality gates |
| Reports | Scheduler morning reports + Research Office publications (post-READY) |
| APIs refresh | Stores/dashboards updated; HTTP APIs are read surfaces |

Failure isolation: alt-data (and similar) can fail → continue with `dataset_unavailable` + operator alert.

---

# 12. Data Storage

| Concern | Code-truth |
| --- | --- |
| **Where stored** | Track-1/HD: filesystem under `KF_STORE_ROOT` / `KF_HD_STORE_ROOT`. Universe: `IUI_STORE_ROOT`. Soft layers (ICI…IMEI): largely **in-memory** process stores. Ask/Scheduler/Research Office: in-process stores. |
| **Versions** | Module version constants (`STACK_VERSION`, `IADI_VERSION`, pipeline versions, publication `knowledge_version` / `evidence_version`). |
| **Point-in-time replay** | HD PIT fields; Universe `members_as_of`; Research Office Publication Registry `historical_replay.replay_id`; IDQ decision replay APIs. |
| **Provenance** | Collector envelopes + field provenance; Ask/RO gates fail without provenance. |
| **Stale detection** | Track-1 `check_freshness` default **72h** max age in validators. Soft seeds may not enforce market-day freshness. |

---

# 13. External Dependencies Table

| Source | Category | Official (declared) | Status | Live | Fixture | Seed | Licensed | Not Configured | Frequency | Used By |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Yahoo Finance | Market | Yahoo | Probe-only | Probe* | **Yes** | | | | on collect | Track-1 company |
| NSE filings | Filings | NSE | Fixture | | **Yes** | | | Live flag → not configured | on collect | Track-1 timeline |
| BSE filings | Filings | BSE | Fixture | | **Yes** | | | | on collect | Track-1 timeline |
| Groww | Portfolio | Groww | Fixture | | **Yes** | | | Live flag → not configured | on collect | Portfolio object |
| RBI macro | Macro | RBI | Fixture | | **Yes** | | | | on collect | Macro object |
| FRED | Macro | FRED | Fixture | | **Yes** | | | | on collect | Macro object |
| World Bank | Macro | WB | Fixture | | **Yes** | | | | on collect | Macro object |
| Nifty registries | Universe | NSE indices (declared) | Seed | | | **Yes** | | | bootstrap | IUI / ICI |
| ICI seeds | Company | curated | Seed | | | **Yes** | | | morning | ICI |
| ICEI seeds | Events | curated | Seed | | | **Yes** | | | morning | ICEI |
| IGRI seeds | Policy | curated | Seed | | | **Yes** | | | morning | IGRI |
| IIVI playbooks | Industry | curated | Seed | | | **Yes** | | | morning | IIVI |
| IERI seeds | Relationships | curated | Seed | | | **Yes** | | | morning | IERI |
| IADI Phase-1 | Alt data | NPCI/POSOCO/… (declared) | Seed | | | **Yes** | | | monthly (meta) | IADI |
| PMI (S&P) | Alt data | S&P Global | Phase-2 shell | | | | **LICENSE REQUIRED** | | — | IADI Phase-2 |
| IMEI Phase-1 | Expectations | company disclosures (declared) | Seed | | | **Yes** | | | morning | IMEI |
| Street consensus | Expectations | vendor TBD | Modular | | | | **LICENSE REQUIRED** | **Default** | — | IMEI Phase-2 |
| HD history | History | synthetic fixture | Fixture | | **Yes** | | | | morning HD | HD |
| IR fundamentals | Derived | internal | Seed/derived | | | **Yes** | | | on produce | Valuation/risk |

\*Yahoo “Live” = HTTP probe only; **payload still fixture**.

---

# 14. Missing Sources (important Indian institutional datasets)

| Missing dataset | Why it matters | Would feed | Expected improvement | Priority |
| --- | --- | --- | --- | --- |
| NSE Bhavcopy | Official EOD prices/volumes | Company / HD / Evidence | Replace Yahoo fixture prices | **P0** |
| BSE Corporate Actions | Dividends, splits, bonuses | ICEI / HD | Event completeness | **P0** |
| NSE Announcements | Material disclosures | ICEI / ICI | Event latency & coverage | **P0** |
| NSE Bulk / Block Deals | Ownership flow signal | IERI / Risk | Flow intelligence | P1 |
| Shareholding Pattern | Promoter/FII/DII structure | ICI ownership | Ownership UNKNOWN → known | **P0** |
| MF / ETF Holdings | Institutional ownership | ICI / IERI | Holder graph | P1 |
| India VIX | Risk regime | Risk / Macro | Regime inputs | P1 |
| FII/DII Flows | Flow regime | Macro / Expectations | Flow context | P1 |
| Open Interest / Options Chain | Derivatives positioning | Expectations / Risk | Positioning | P2 |
| CDSL / NSDL | Demat / corp action truth | Ownership / Events | Settlement truth | P1 |
| MCA filings | Governance / charges / directors | ICI / ICEI / Gov | Governance depth | **P0** |
| RBI DBIE | Official macro time series | Macro / IADI credit | Replace macro fixture | **P0** |
| MOSPI (live IIP etc.) | Official activity | IADI | Replace IIP seed | P1 |
| Power Exchange / Grid live | Power demand | IADI electricity | Live industrial proxy | P1 |
| Coal India / coal stocks | Energy/input | IADI Phase-2 | Commodity ops | P2 |
| DGFT | Trade policy | IGRI trade | Live trade policy | P1 |
| GSTN published (live) | Formal economy | IADI GST | Live GST | P1 |
| NPCI UPI (live) | Digital payments | IADI UPI | Live UPI | P1 |
| SEBI filings / LODR live | Regulatory | IGRI / ICEI | Live reg | P1 |
| Exchange guidance XBRL | Expectations | IMEI | Real guidance | **P0** |
| Licensed consensus | Street estimates | IMEI | Expectation gaps | P1 (license) |
| PMI (S&P) | Manufacturing pulse | IADI | Leading indicator | P2 (**LICENSE REQUIRED**) |

---

# 15. Final Source Architecture (as implemented)

```text
Official Sources (declared)
        │
        ▼  [mostly NOT connected live]
Collectors (Yahoo probe* / NSE·BSE·Groww·RBI·FRED·WB fixtures
            + soft-layer seed collectors)
        │
        ▼
Validators (Track-1 validate_dataset; layer gates; freshness 72h)
        │
        ▼
Derived Producers (valuation, accounting, BQ, risk, revisions, surprises…)
        │
        ▼
Knowledge Objects (file KF/HD/IUI + in-memory soft layers)
        │
        ▼
Evidence Packs (Track-1 packs + evidence_feed soft aggregate
                + Ask evidence assembly)
        │
        ▼
Research Office (knowledge-only publications; post READY)
        │
        ▼
Ask Pipeline (KF primary retrieval → packs → govern_answer)
        │
        ▼
Institutional Reasoning Phase 1–7 (consume packs; no fetch)
        │
        ▼
Portfolio Intelligence (conditional)
        │
        ▼
Decision Quality (record/observability)
        │
        ▼
Outcome Intelligence (track / evaluate)
        │
        ▼
Continuous Adaptive Learning (propose → approve → overlay; never auto)
```

\*Yahoo probe does not replace fixture payloads.

---

# Final lists

### 1. Every source currently “live”
- **None for institutional data payloads.**
- Optional **Yahoo connectivity probe** when `KF_LIVE_YAHOO` is set — still serves **fixture** primitives/prices.

### 2. Every source running on fixtures
- Yahoo company payloads (always fixture panel/prices)
- NSE filings fixture
- BSE filings fixture
- Groww portfolio book fixture
- RBI / FRED / World Bank macro fixtures
- Historical Depth seed history
- Universe reconstitution events

### 3. Every licensed dependency
- **Street consensus feed** — `AGIB_LICENSED_CONSENSUS_PROVIDER` → **LICENSE REQUIRED / NOT CONFIGURED → UNKNOWN**
- **PMI manufacturing (S&P Global)** — Phase-2 shell → **LICENSE REQUIRED** (not ingested; IIP seed used instead)

### 4. Every missing source (high level)
See §14 — notably NSE Bhavcopy, NSE Announcements, BSE Corporate Actions, Shareholding Pattern, MCA, live RBI DBIE, live NPCI/GSTN/MOSPI/Grid, FII/DII, VIX, OI/options, CDSL/NSDL, licensed consensus, PMI.

### 5. Overall source maturity score
**3.5 / 10**

### 6. Biggest gaps blocking “definitive Indian institutional platform”
1. **No live official price/volume/corporate-action ingestion** (Bhavcopy / announcements / corp actions).  
2. **Ownership blank** (shareholding / CDSL-NSDL / MF holdings).  
3. **Soft layers are curated seeds**, not refreshed official corpora (gov/alt/expectations).  
4. **Licensed consensus absent** → expectation gaps cannot be institutional-grade vs street.  
5. **In-memory soft stores** → weak durability/ops continuity vs filesystem Track-1/HD.  
6. **Morning “06:00” is metadata + API**, not a guaranteed production cron in-repo.

---

## Labelling cheat-sheet for readers

| Label | Meaning |
| --- | --- |
| LIVE | Code fetches external payload used as knowledge |
| FIXTURE | Deterministic test/demo payload used as knowledge |
| SEED | Curated institutional corpus checked into repo |
| DERIVED | Computed from other objects |
| NOT IMPLEMENTED | Declared/priority/env path exists but does not ingest |
| LICENSE REQUIRED | Needs commercial feed; returns UNKNOWN / deferred |
| UNKNOWN | Field/value unavailable without fabrication |
| NOT CONFIGURED | Env/provider unset |

---

*End of code-truth Knowledge Source Audit.*
