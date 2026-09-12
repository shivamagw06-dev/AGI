# AGIB Phase 2 — Institutional Investment Intelligence Programme

```text
BASELINE:   AGIB Institutional Baseline v1.0 (FROZEN)
STATUS:     PROGRAMME SPEC — ready for implementation
OBJECTIVE:  Improve investment intelligence quality — not governance
UPDATED:    2026-07-29
```

**Primary question this programme answers:**  
*Can AGIB produce deeper, more accurate, more explainable investment research while every Phase 1 institutional guarantee remains intact?*

---

## 0. Relationship to Baseline v1.0

Phase 1 established research **governance**. That stack is frozen:

| Frozen component | Rule |
| --- | --- |
| Constitution | Do not modify |
| Governance Spec (GOV-001+) | Do not modify |
| Decision Engine contracts | Do not modify |
| Institutional Gate | Do not modify |
| Recommendation / Institutional Readiness methodology | Do not modify |
| Analytical Confidence methodology | Do not modify |
| Evaluation Lab | Do not modify |
| Drift Engine | Do not modify |
| Institutional Acceptance Test (IAT) | Do not modify |
| Mission Control / Release Observability | Do not modify |

Phase 2 **extends intelligence inputs** into the existing pipeline. It does **not** replace the baseline.

```text
Investment Committee
        │
        ▼
Existing Intelligence Engines
        │
        ▼
NEW Phase 2 Engines   ← this programme
        │
        ▼
Decision Engine        (frozen contracts)
        │
        ▼
Institutional Gate     (frozen thresholds)
        │
        ▼
Governance Spec
        │
        ▼
Evaluation Lab
        │
        ▼
Drift Engine
        │
        ▼
Institutional Acceptance Test
```

**Success is measured only if IAT continues to PASS, UNKNOWN drift = 0, and no governance regression — while evidence depth and analytical confidence improve where warranted.**

> Note: Earlier repo docs named “Phase 2” (Evidence Graph / Analog) are a prior programme numbering. This document is **AGIB Institutional Baseline v1.0 → Phase 2 Investment Intelligence** and supersedes that label for post-baseline work.

---

## 1. Architecture

### 1.1 Design principles

1. **Intelligence, not governance** — new modules improve research quality; they never redefine gates or GOV rules.
2. **Soft integration** — Phase 2 packages expose `package_for_ask_agi` / `soft_slice` façades; Decision Engine consumes optional enrichment.
3. **Evidence-first** — every forecast, value, and ownership claim carries lineage, freshness, and confidence.
4. **Sector-aware** — valuation and KPI selection are playbook-driven, not one-size-fits-all.
5. **Measurable delta** — every sprint publishes metrics vs Baseline v1.0 on Golden 200.
6. **Fail soft** — missing Phase 2 evidence lowers *confidence/coverage*, never silently invents conviction.

### 1.2 Logical architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     Data & Market Fabric                      │
│  Filings · Financials · Ownership · Consensus · Live Market   │
└────────────────────────────┬────────────────────────────────┘
                             │
     ┌───────────┬───────────┼───────────┬───────────┬────────┐
     ▼           ▼           ▼           ▼           ▼        ▼
  P2.1        P2.2        P2.3        P2.4        P2.5     P2.6
 Earnings   Valuation   Ownership   Catalyst    Sector    Live
 Intel      Intel       Intel       Intel       Playbooks Context
     │           │           │           │           │        │
     └───────────┴───────────┴─────┬─────┴───────────┴────────┘
                                   ▼
                    Company Analysis / CID enrichment
                                   │
                                   ▼
                         Decision Engine (frozen)
                                   │
                                   ▼
                      Institutional Gate (frozen)
```

### 1.3 Dependency order (implementation)

| Priority | Workstream | Why first? | Expected impact |
| ---: | --- | --- | --- |
| 1 | **P2.6 Live Market Context** | Accurate current market context without changing research | High |
| 2 | **P2.3 Ownership Intelligence** | Addresses a top cause of Institutional Readiness failures | Very High |
| 3 | **P2.1 Earnings Intelligence** | Forward-looking analysis; thesis quality | Very High |
| 4 | **P2.2 Valuation Intelligence** | Sector-appropriate intrinsic value | High |
| 5 | **P2.5 Sector Playbooks** | Sector-specific consistency | Medium–High |
| 6 | **P2.4 Catalyst Intelligence** | What could change the thesis | Medium |

```text
P2.6 Live Market Context
        │
P2.3 Ownership Intelligence
        │
P2.1 Earnings Intelligence
        │
P2.2 Valuation Intelligence
        │
P2.5 Sector Intelligence
        │
P2.4 Catalyst Intelligence
```

Starting with **P2.6 + P2.3** improves evidence quality without changing the governance framework.

### 1.3b Capability milestones (preferred naming)

Rather than a monolithic “Phase 2”, deliver capability milestones. Each ends with a full Evaluation Lab run + IAT.

| Milestone | Name | Workstreams |
| --- | --- | --- |
| **Phase 2.1** | Market & Ownership Intelligence | P2.6 → P2.3 |
| **Phase 2.2** | Earnings & Valuation Intelligence | P2.1 → P2.2 |
| **Phase 2.3** | Sector & Catalyst Intelligence | P2.5 → P2.4 |

**Sprint 1 (Phase 2.1):** P2.6 Live Market Context — market-aware recommendations; fail-closed quotes; no governance changes.  
**Sprint 2 (Phase 2.1):** P2.3 Ownership Intelligence — reduce deferrals from missing ownership packs.  
**Then:** P2.1 Earnings Intelligence (largest effort; benefits from market + ownership).

Architectural design is **complete**. Highest-value work is implementing engines, measuring impact, and proving improvement vs Baseline v1.0.

### 1.3c Implementation PR checklist (mandatory)

Every implementation PR must answer:

1. What intelligence did we add?
2. What measurable metric improved?
3. What metric stayed unchanged?
4. Did IAT still pass?
5. Did UNKNOWN drift remain zero?

If those answers are not clear, the implementation is **not ready to merge**.

### 1.4 Standard engine contract (mandatory)

Every Phase 2 engine **must** expose the same interface so Integration Lab, Decision Engine soft slices, and IAT can treat engines uniformly.

```text
Engine Name
    <e.g. Ownership Intelligence>

Version
    v1.0

Inputs
    Company Pack
    Live Data
    Knowledge Graph
    (+ module-specific)

Outputs
    Score / Outlook (engine-specific)
    Evidence
    Confidence
    Freshness
    Lineage

Consumers
    Decision Engine
    Evaluation Lab

Dependencies
    Knowledge Factory
    Market Context
    (+ module-specific)

Failure Mode
    Degrade gracefully
    Do not block unrelated engines
```

**Machine contract** (see `phase2_investment_intelligence/contract.py`):

```json
{
  "engine": "ownership_intelligence",
  "version": "p2.3-v1.0.0",
  "inputs": ["company_pack", "live_data", "knowledge_graph"],
  "outputs": {
    "score": null,
    "evidence": [],
    "confidence": 0.0,
    "freshness": {"age_days": null, "stale": false, "sla_days": null},
    "lineage": []
  },
  "consumers": ["decision_engine", "evaluation_lab"],
  "dependencies": ["knowledge_factory", "live_market_context"],
  "failure_mode": {
    "strategy": "degrade_gracefully",
    "block_unrelated_engines": false,
    "fabricated": false
  },
  "baseline_compatible": true
}
```

Rules:

1. Missing inputs → return `enabled=true` with empty/partial outputs + low confidence — **never** raise into Ask AGI.
2. `fabricated` must be `false`; inventing ownership or earnings is a Phase 1 violation.
3. Engines may improve *evidence* that feeds the frozen gate; they must not change gate thresholds.
4. Unit tests assert the standard envelope keys on every `package_for_ask_agi` / `analyse` response.

---

## 2. Module specifications

### P2.1 — Earnings Intelligence (`earnings_intelligence`)

**Purpose:** Institutional earnings outlook separate from company quality.

| Capability | Description |
| --- | --- |
| Revenue / EPS / EBITDA / Margin forecasting | Multi-horizon (Q+1…Q+4, FY+1…FY+2) |
| Consensus aggregation | Broker / street estimate blend with source weights |
| Revision tracking | 30/90-day estimate revision slopes |
| Surprise prediction | Probabilistic beat/miss vs consensus |
| Guidance extraction | From filings / transcripts (soft FIL/FDI hooks) |
| Guidance history | Stated vs delivered |
| Quarterly trend analysis | Sequential and YoY |
| Forecast confidence | Calibrated; never conflated with company quality |
| Estimate dispersion | Cross-analyst disagreement |
| Historical forecast accuracy | Rolling MAPE / bias by ticker & sector |

**Outputs (contract):**

```json
{
  "ticker": "ETERNAL",
  "revenue_outlook": {},
  "eps_outlook": {},
  "margin_outlook": {},
  "forecast_confidence": 0.0,
  "revision_trend": "up|flat|down",
  "earnings_risk": {},
  "lineage": [],
  "freshness": {}
}
```

**Must not:** Change Recommendation Readiness thresholds. May only *supply* evidence that the gate already knows how to score.

---

### P2.2 — Valuation Intelligence (`valuation_intelligence`)

**Purpose:** Multi-model intrinsic value with sector-selected methodology.

| Model family | Models |
| --- | --- |
| Cash-flow | Multi-stage DCF, Residual Income, DDM |
| Relative | EV/EBITDA, EV/Sales, P/E, PEG, P/B |
| Asset | SOTP, Replacement Cost, NAV, Embedded Value |

**Sector auto-select (examples):**

| Sector | Primary | Secondary |
| --- | --- | --- |
| Banks / NBFC | P/B, Residual Income | SOTP |
| Insurance | Embedded Value | P/B |
| IT / Consumer Internet | Multi-stage DCF, EV/Sales | P/E |
| Power / Utilities / REIT | DDM / NAV | EV/EBITDA |
| Metals / Commodities | EV/EBITDA + cycle adj. | Replacement cost |
| Pharma / Auto / Cap Goods | DCF + EV/EBITDA | Peer P/E |

**Outputs:** Intrinsic Value · Margin of Safety · Valuation Confidence · Sensitivity · Valuation Drivers.

**Must not:** Override Institutional Gate when valuation evidence is thin — return `valuation_confidence` low and leave thesis INCONCLUSIVE if required.

---

### P2.3 — Ownership Intelligence (`ownership_intelligence`)

**Purpose:** Close the Phase 1 evidence gap that most often fails Institutional Readiness (shareholding pack).

| Track | Fields |
| --- | --- |
| Promoter | holding %, pledge %, trend |
| Institutions | FII, DII, mutual fund |
| Insiders | buy / sell clusters |
| Market structure | block / bulk deals |
| Structure | concentration, quarterly evolution |

**Outputs:** Ownership Quality · Institutional Accumulation · Governance Signals · Ownership Risk.

**Integration priority:** Highest for Golden 200 names currently failing “Shareholding current”.

---

### P2.4 — Catalyst Intelligence (`catalyst_intelligence`)

**Purpose:** Forward value drivers with probability and timing — extends existing `catalyst_trigger_intelligence` / FIE catalysts without replacing them.

| Class | Examples |
| --- | --- |
| Company | Earnings, guidance, buybacks, capacity, launches, M&A |
| Policy | RBI, Budget, sector regulation |
| Macro | Commodity, FX, credit cycle |

**Outputs:** Catalyst Calendar · Impact · Probability · Timing.

---

### P2.5 — Sector Intelligence (`sector_intelligence_playbooks`)

**Purpose:** Sector-specific institutional playbooks (KPIs, valuation framework, risk model, peer method).

**Sectors (v1 set):** Banks, NBFC, IT, Power, Utilities, Defence, Auto, Pharma, Capital Goods, FMCG, Insurance, Real Estate, Telecom, Metals, Chemicals, Consumer Internet.

Each playbook:

```text
sector_kpis
valuation_framework
operating_metrics
risk_model
earnings_drivers
peer_comparison_methodology
```

Consumes / extends: `continuous_sector_knowledge`, `peer_intelligence`, `institutional_playbooks` — does not fork Decision Engine sector weights.

---

### P2.6 — Live Market Context (`live_market_context`)

**Purpose:** Honest live market framing for timing — never a substitute for research.

| Input | Use |
| --- | --- |
| Live price / volume / delivery | Market context panel |
| Volatility / relative strength | Timing risk |
| Distance to intrinsic value | Uses P2.2 when available |
| Liquidity / breadth | Position sizing context only |

**Rule:** Refresh market context only. Never invalidate institutional research unless Governance Spec requires it.

**Hard requirement:** No seeded NIFTY fallback for non-index tickers (Eternal-class failure mode). Fail closed → `price_available=false` → gate/valuation stale paths already defined in Phase 1.

---

## 3. Folder structure

```text
intelligence-engine/
  phase2_investment_intelligence/          # programme registry (this PR)
    schema.py
    production.py
    workstreams.py
    __main__.py
    README.md

  earnings_intelligence/                   # P2.1
    schema.py
    models/          # revenue, eps, ebitda, margin
    consensus/
    revisions/
    surprise/
    guidance/
    accuracy/
    production.py
    store.py
    api/
    tests/

  valuation_intelligence/                  # P2.2
    schema.py
    models/          # dcf, ri, ddm, sotp, multiples, nav, ev
    sector_select.py
    sensitivity/
    production.py
    store.py
    api/
    tests/

  ownership_intelligence/                  # P2.3
    schema.py
    promoters/
    institutions/
    insiders/
    deals/
    trends/
    production.py
    store.py
    api/
    tests/

  catalyst_intelligence/                   # P2.4 (may wrap catalyst_trigger_intelligence)
    schema.py
    calendar/
    scoring/
    production.py
    store.py
    api/
    tests/

  sector_intelligence_playbooks/           # P2.5
    schema.py
    playbooks/       # banks.yaml … chemicals.yaml
    kpis/
    production.py
    tests/

  live_market_context/                     # P2.6
    schema.py
    groww_bridge.py
    yahoo_failover.py
    context_panel.py
    production.py
    tests/
```

Existing modules (`forecast_intelligence`, `filing_intelligence/ownership`, `company_analysis/valuation_intel.py`, `peer_intelligence`, `catalyst_trigger_intelligence`) remain **providers**. Phase 2 packages are the institutional façades that normalise contracts for Decision Engine soft consumption.

---

## 4. APIs

All under Intelligence Engine `/v1`. Soft, read-oriented; never mutate gate thresholds.

| Method | Path | Module |
| --- | --- | --- |
| GET | `/phase2/health` | Programme registry |
| GET | `/phase2/contracts` | Standard engine contracts |
| GET | `/phase2/scorecard` | Intelligence Scorecard templates |
| GET | `/phase2/workstreams` | Catalogue + status |
| GET | `/earnings-intelligence/health` | P2.1 |
| GET/POST | `/earnings-intelligence/{ticker}` | Outlook pack |
| GET | `/valuation-intelligence/health` | P2.2 |
| GET/POST | `/valuation-intelligence/{ticker}` | Intrinsic pack |
| GET | `/ownership-intelligence/health` | P2.3 |
| GET/POST | `/ownership-intelligence/{ticker}` | Ownership pack |
| GET | `/catalyst-intelligence/health` | P2.4 |
| GET/POST | `/catalyst-intelligence/{ticker}` | Calendar pack |
| GET | `/sector-playbooks/health` | P2.5 |
| GET | `/sector-playbooks/{sector}` | Playbook |
| GET | `/live-market-context/health` | P2.6 |
| GET | `/live-market-context/{ticker}` | Context panel |

**Ask AGI / IEL integration:** each module exposes `package_for_ask_agi(query, ticker=...)` returning `{enabled, soft, ...}` for existing soft-slice patterns in `company_analysis` / `decision_engine.layers` — **additive fields only**.

---

## 5. Data models (canonical contracts)

### 5.1 Shared envelope

```json
{
  "ticker": "string",
  "as_of": "ISO-8601",
  "module": "earnings_intelligence",
  "version": "p2.1-v1.0.0",
  "confidence": 0.0,
  "freshness": {"age_days": 0, "stale": false},
  "lineage": [{"source": "", "ref": "", "retrieved_at": ""}],
  "fabricated": false,
  "baseline_compatible": true
}
```

### 5.2 Earnings

`RevenueOutlook | EpsOutlook | MarginOutlook` → `{horizon, point, low, high, consensus, revision_30d, revision_90d, dispersion, unit}`

### 5.3 Valuation

```json
{
  "method_primary": "multi_stage_dcf",
  "methods_used": ["multi_stage_dcf", "ev_ebitda"],
  "intrinsic_value": null,
  "price": null,
  "margin_of_safety_pct": null,
  "valuation_confidence": 0.0,
  "sensitivity": [],
  "drivers": []
}
```

### 5.4 Ownership

```json
{
  "promoter_pct": null,
  "promoter_pledge_pct": null,
  "fii_pct": null,
  "dii_pct": null,
  "mf_pct": null,
  "insider_flow_90d": null,
  "block_bulk_90d": [],
  "ownership_quality": null,
  "accumulation_signal": null,
  "ownership_risk": null,
  "as_of_quarter": null
}
```

### 5.5 Catalyst

`{id, class, title, impact[-1..1], probability[0..1], timing_window, evidence[]}`

### 5.6 Live context

`{ltp, currency, volume, delivery_pct, volatility, relative_strength, distance_to_iv_pct, liquidity_score, breadth_context, source, stale}`

---

## 6. Database schema

Prefer Postgres (Supabase) for durable packs; JSON artifact mirror under module `store/` for IEL replay.

```sql
-- Phase 2 shared
create table if not exists p2_module_runs (
  id uuid primary key default gen_random_uuid(),
  module text not null,
  ticker text not null,
  as_of timestamptz not null,
  version text not null,
  confidence numeric,
  freshness_age_days numeric,
  payload jsonb not null,
  lineage jsonb not null default '[]',
  created_at timestamptz not null default now()
);
create index if not exists p2_module_runs_ticker_module_idx
  on p2_module_runs (ticker, module, as_of desc);

create table if not exists p2_earnings_forecasts (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  horizon text not null,
  metric text not null, -- revenue|eps|ebitda|margin
  point numeric,
  low numeric,
  high numeric,
  consensus numeric,
  revision_30d numeric,
  revision_90d numeric,
  dispersion numeric,
  model_version text not null,
  as_of timestamptz not null,
  lineage jsonb not null default '[]'
);

create table if not exists p2_valuation_results (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  method_primary text not null,
  intrinsic_value numeric,
  margin_of_safety_pct numeric,
  valuation_confidence numeric,
  sensitivity jsonb,
  drivers jsonb,
  as_of timestamptz not null,
  lineage jsonb not null default '[]'
);

create table if not exists p2_ownership_snapshots (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  as_of_quarter text not null,
  promoter_pct numeric,
  promoter_pledge_pct numeric,
  fii_pct numeric,
  dii_pct numeric,
  mf_pct numeric,
  ownership_quality numeric,
  accumulation_signal text,
  ownership_risk text,
  raw jsonb not null,
  lineage jsonb not null default '[]',
  unique (ticker, as_of_quarter)
);

create table if not exists p2_catalysts (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  class text not null,
  title text not null,
  impact numeric,
  probability numeric,
  timing_window text,
  evidence jsonb not null default '[]',
  as_of timestamptz not null
);

create table if not exists p2_market_context (
  ticker text not null,
  as_of timestamptz not null,
  ltp numeric,
  source text not null,
  stale boolean not null default false,
  payload jsonb not null,
  primary key (ticker, as_of)
);

create table if not exists p2_eval_deltas (
  id uuid primary key default gen_random_uuid(),
  release_id text not null,
  workstream text not null,
  metric text not null,
  baseline_value numeric,
  current_value numeric,
  delta numeric,
  created_at timestamptz not null default now()
);
```

RLS: service-role write; authenticated read for mission-control surfaces only.

---

## 7. Interfaces with existing engines

| Existing engine | Phase 2 interaction |
| --- | --- |
| `filing_intelligence` / `guidance` / `ownership` | Upstream extractors for P2.1 / P2.3 |
| `forecast_intelligence` + `forecast_validation_learning` | Calibration backbone for P2.1 accuracy |
| `company_analysis.valuation_intel` | Superseded *softly* by P2.2 façade; keep as fallback |
| `peer_intelligence` | Peer multiples + sector ranks for P2.2 / P2.5 |
| `catalyst_trigger_intelligence` | Event stream for P2.4 |
| `continuous_sector_knowledge` / `institutional_playbooks` | Seed P2.5 playbooks |
| `forecast_provider_integration` / Groww | P2.6 live path; fix ETERNAL-class seed bug |
| `cid` / `company_analysis` | Attach Phase 2 packs in soft slices |
| `decision_engine` | **Consume only** via optional layer evidence — no contract edits |
| `institutional_evaluation_lab` | Scorecards read new evidence fields; runner unchanged |
| `governance_spec` | Unchanged; GOV rules still bind outputs |
| `iat` | Remains qualification gate for any future baseline |

---

## 8. Integration points (code-level)

1. **Soft slice registration** — `institutional_stack` / `company_analysis` assembly adds optional keys:
   - `earnings_intelligence`
   - `valuation_intelligence`
   - `ownership_intelligence`
   - `catalyst_intelligence`
   - `sector_playbook`
   - `live_market_context`
2. **Decision Engine** — layers already accept evidence lists; Phase 2 appends evidence strings + structured side-car under `live_evidence` / CID. **No new layer IDs that redefine weights** without a future IAT.
3. **Ask AGI** — `UiService.search` already merges soft packages; enable flags per module (`EARNINGS_INTELLIGENCE=1`, etc.).
4. **IEL Golden runner** — `per_ticker.py` may *call* new façades for pack enrichment; failure taxonomy gains reasons like `OWNERSHIP_STALE` already aligned with gate checklist.
5. **Observability / IAT** — new coverage pillars reported as evidence metrics; thresholds unchanged unless a future IAT freezes Baseline v1.1.

---

## 9. Test strategy

| Level | What | Gate |
| --- | --- | --- |
| Unit | Each model / parser / sector selector | CI on PR |
| Contract | JSON schema + `fabricated=false` + lineage present | CI |
| Golden soft | 20-name subset from Golden 200 | PR check |
| Golden full | 200-name Evaluation Lab run | merge to main |
| Governance | Phase 6 GOV-001…008 | must PASS |
| Drift | vs Baseline v1.0 release | UNKNOWN = 0, budget PASS |
| IAT | Full Institutional Acceptance Test | must PASS |
| Freeze guard | Diff check — forbidden paths untouched | CI |

**Forbidden-path CI grep (illustrative):**

```text
decision_engine/readiness_gate.py
governance_spec/v1_0/rules.py
governance_spec/schema.py
# constitution constants / readiness thresholds
```

Any PR touching forbidden paths fails CI unless labelled `baseline-amendment` **and** accompanied by a new IAT report.

---

## 10. Evaluation methodology

Phase 1 measured **governance**. Phase 2 measures **intelligence** — while re-checking that governance never regresses.

### 10.1 Intelligence Scorecard (per workstream)

Every workstream release must publish an Intelligence Scorecard:

| Metric | Target | Notes |
| --- | --- | --- |
| Coverage | ≥95% | Share of Golden 200 with usable engine output |
| Freshness | Within SLA | Per-engine SLA (e.g. ownership ≤ 45d, price = live/session) |
| Confidence | Reported | Always present; never silently omitted |
| Explainability | Present | Evidence + lineage non-empty when score present |
| IAT regressions | 0 | Full IAT still PASS |
| UNKNOWN drift | 0 | Drift budget vs prior release |
| Average runtime | Within budget | Per-engine budget (default ≤ 2.0s p50 on pack path) |

Scorecard artifact:

```text
results/{release}/_intelligence_scorecard_{workstream}.json
results/{release}/_intelligence_scorecard_{workstream}.md
```

Programme roll-up:

```text
results/{release}/_phase2_intelligence_scorecard.json
```

### 10.2 Baseline delta (still required)

Every Phase 2 sprint also publishes a **Baseline Delta Report** against AGIB Institutional Baseline v1.0:

| Metric | Direction | Source |
| --- | --- | --- |
| Analytical Confidence (avg) | ↑ | IEL summary |
| Institutional Readiness (avg) | ↑ where evidence added | Gate coverage |
| Evidence coverage % | ↑ | IEL / IAT evidence area |
| Ownership pillar % | ↑ | P2.3 |
| Valuation completeness % | ↑ | P2.2 |
| Forecast accuracy (MAPE) | ↓ error | P2.1 accuracy store |
| Recommendation quality proxy | ↑ (judge / CIO exam) | IEL judges / IIEX |
| Governance critical fails | = 0 | Phase 6 |
| UNKNOWN drift | = 0 | Drift engine |
| IAT overall | PASS | IAT |

### 10.3 Definition of Done (every workstream)

A Phase 2 module is **complete** only when **all** of the following are true:

| # | Requirement |
| --: | --- |
| 1 | Architecture implemented (standard engine contract) |
| 2 | Unit and integration tests passing |
| 3 | Evaluation Lab integrated (soft consumption + scorecard) |
| 4 | No governance regressions (Phase 6 critical fails = 0) |
| 5 | UNKNOWN drift remains 0 |
| 6 | Institutional Acceptance Test still PASS |
| 7 | Demonstrable improvement on ≥1 defined intelligence metric |

Examples for #7:

- **P2.3** — fewer recommendation deferrals / readiness fails due to missing shareholding; ownership coverage ≥95% on Golden 200
- **P2.6** — zero false seed LTPs; live/failover price coverage ≥95%
- **P2.1** — forecast completeness / confidence reported for ≥95% of names with financials
- **P2.2** — valuation completeness (intrinsic or explicit inconclusive + confidence) ≥95%

Incomplete modules stay `status: specified | in_progress` in the programme registry and remain feature-flagged **off** in production Ask AGI.

---

## 11. Migration plan

| Stage | Action |
| --- | --- |
| M0 | Land programme registry (this document + `phase2_investment_intelligence`) |
| M1 | P2.6 live price honesty — fail closed, no wrong seed LTP |
| M2 | P2.3 ownership packs for Golden 200 (unblocks readiness) |
| M3 | P2.1 earnings façade over FIL/FIE/consensus |
| M4 | P2.5 playbook YAML v1 for 15 sectors |
| M5 | P2.2 sector-selected valuation |
| M6 | P2.4 catalyst calendar normalisation |
| M7 | Full Golden 200 + IAT re-qualification (Baseline remains v1.0; delta reported) |

No cut-over that disables Phase 1 paths. Feature flags default **off** in production until soft Golden 20 passes.

---

## 12. Rollout plan

```text
Week-slice rollout (engineering slices, not calendar promises):

Slice A  Programme registry + freeze-guard CI
Slice B  P2.6 Live Market Context
Slice C  P2.3 Ownership Intelligence (Golden 200 backfill)
Slice D  P2.1 Earnings Intelligence (Nifty 50 → Next 50 → full 200)
Slice E  P2.5 Sector Playbooks v1
Slice F  P2.2 Valuation Intelligence
Slice G  P2.4 Catalyst Intelligence
Slice H  Golden 200 eval + Drift + IAT certification report
```

**Release naming:** `P2.<workstream>-<semver>` (e.g. `P2.1-v1.0.0`).  
**Promotion rule:** module enabled in Ask AGI only after:

1. Unit + contract tests green  
2. Soft Golden 20  
3. Phase 6 PASS  
4. Drift budget PASS vs prior release  
5. IAT PASS  

**Baseline policy:** Baseline v1.0 remains source of truth. A future **Baseline v1.1** requires a dedicated IAT PASS and an explicit freeze prompt — never an implicit rewrite.

---

## Prohibited (restate)

Do **not**:

- redesign Constitution, Governance Spec, Evaluation Lab, Decision Engine  
- redesign Recommendation / Institutional Readiness / Analytical Confidence methodology  
- redesign Phase 1 architecture  
- expand GOV-001+ inside Phase 2 PRs  

Phase 2 extends intelligence. Phase 2 does not replace the baseline.

---

## Deliverable checklist

| # | Deliverable | Location |
| --: | --- | --- |
| 1 | Architecture | §1 |
| 1a | Standard engine contract | §1.4 · `contract.py` |
| 2 | Module specifications | §2 |
| 3 | Folder structure | §3 |
| 4 | APIs | §4 · `/phase2/contracts` · `/phase2/scorecard` |
| 5 | Data models | §5 |
| 6 | Database schema | §6 |
| 7 | Interfaces with existing engines | §7 |
| 8 | Integration points | §8 |
| 9 | Test strategy | §9 |
| 10 | Evaluation methodology + Intelligence Scorecard + DoD | §10 |
| 11 | Migration plan | §11 |
| 12 | Rollout plan | §12 |
| — | Machine-readable registry | `intelligence-engine/phase2_investment_intelligence/` |

---

## Next implementation prompt (recommended)

Start with **P2.6 + P2.3** (live price honesty + ownership packs): they unlock Institutional Readiness for names like Eternal without touching frozen gate math — then **P2.1 Earnings Intelligence** for the highest investment-impact lift.
