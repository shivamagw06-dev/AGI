# IMPLEMENTATION MASTER PROGRAMME V1  
## Official Execution Roadmap — AGI Investment Office

**Document ID:** `IMP-V1`  
**Filename:** `IMPLEMENTATION_MASTER_PROGRAMME_V1.md`  
**Architecture basis:** **E00 Architecture v1.0 — FEATURE FROZEN**  
**Governing specs (immutable unless E00-amended):** E00, ORCH, L4, E01–E05, E08–E11, E13–E14  
**Status:** Official engineering execution programme  
**Version:** 1.0.0  
**Owner:** Head of Research Engineering / Head of Quantitative Research / CIO  
**Horizon:** **12–18 months** to Production v1; Institutional Platform v2 thereafter  
**Nature:** **Execution roadmap only** — no architecture redesign

### Programme law

1. Architecture v1.0 is **feature frozen**. This document schedules **implementation**, not redesign.  
2. Every work item must cite a frozen spec section (E00 / ORCH / L4 / E0X).  
3. ORCH is the only legal integration surface for engines.  
4. E03 remains Production primary until L4 statistical superiority + promotion vote.  
5. Research-only forever under E00 §1.5 (paper trading ≠ brokerage execution).  
6. Promotion requires §10 validation gates — no shortcut to Production.

### Working-backwards outcome

**Press-release test (Amazon-style):**  
> AGI Investment Office publishes a daily, evidence-backed institutional research seal: regime, risk, cross-sectional ranks, composite opinion (shadow→primary), illustrative portfolios, and CIO brief — all auditable to EngineState hashes — without placing a single order.

---

# 1. Executive Summary

## 1.1 Overall mission

Deliver a **working, observable, flag-gated Investment Office** that implements frozen Architecture v1.0 end-to-end: data → features → engines → L4 → E10 → research generation → distribution → monitoring — under ORCH control.

## 1.2 Current status (baseline)

| Area | Status |
|------|--------|
| Architecture specs | **Frozen** (E00, ORCH, L4, engine set) |
| Production AGI technical score | **Live** (`score_research` / E03 `SM_AGI_TECH` compat path) |
| Macro / market desks | **Partial** product surfaces; not full E01/E14 contracts |
| EngineState / Feature Registry / ORCH | **Specified; not Production-implemented** |
| L4 / E10 / specialised engines | **Specs only / flags off** |
| Paper trading | **Not started** |
| Institutional validation harness | **Partial / ad hoc** |

## 1.3 Architecture maturity

| Layer | Spec maturity | Build maturity |
|-------|---------------|----------------|
| L0–L2 | Frozen in E00/ORCH | Partial ingest; registry incomplete |
| L3 engines | Frozen specs | E03 tech path strongest; others greenfield |
| L4 | Frozen | Not built (shadow planned) |
| L5 E10 | Frozen | Not built (flagged) |
| L6–L8 | Frozen principles | Partial UI/publish; ORCH monitor absent |
| ORCH | Frozen | Not built |

**Verdict:** Architecture **complete**; engineering **early Programme Phase 0–1**.

## 1.4 Remaining work (programme scope)

1. Core platform + ORCH scheduler/run ledger  
2. Market data + validation + Feature Registry  
3. P0 for every frozen engine + L4 shadow + E10 candidate  
4. Historical validation / calibration gates  
5. Paper trading research loop (no broker OMS)  
6. Internal CIO → Beta → Production v1 → Institutional v2  

## 1.5 Critical path

```
Platform+ORCH → Feature Registry → E01 → E14 → E03 contractisation
  → L4 shadow → Validation gates → Internal CIO
  → E10 flagged → Beta website → Production v1
```

Specialised engines (E04/E05/E08/E09/E11/E13) run **parallel** off the critical path but block L4 “full voter” and Institutional v2 richness.

---

# 2. Programme Structure

## 2.1 Workstreams

| ID | Workstream | Owns | Primary specs |
|----|------------|------|---------------|
| **WS01** | Core Platform | Packages, contracts, auth, shared libs, CI | E00 §5,§13–§15,§19; ORCH §17 |
| **WS02** | Market Data Platform | L0 ingest, vendors, staging | E00 §2.1; ORCH L0 |
| **WS03** | Feature Registry | L1/L2, PIT, online store | E00 §2.2–2.3,§6; ORCH §4 |
| **WS04** | Research Engines | E01–E05,E08,E09,E11,E13,E14 | Engine specs |
| **WS05** | Composite Intelligence | L4 fusion, explanation, shadow | L4; E00 §2.5,§11–§12 |
| **WS06** | Portfolio Construction | E10 views→weights | E10; E00 §2.6 |
| **WS07** | Frontend Platform | Dashboards, beta, admin | E00 §15; engine UI sections |
| **WS08** | Research Generation | CIO brief, notes, LLM polish claim-bound | E00 §2.7; L4/E14 |
| **WS09** | Backtesting Platform | Replay, walk-forward, costs | E00 §16; ORCH §7.6 |
| **WS10** | Paper Trading | Simulated books, TCA research, no orders | E10/E14; future exec constitution out of scope |
| **WS11** | Monitoring & Observability | Metrics, traces, SLOs, L8 | ORCH §11; E00 §2.9 |
| **WS12** | Production Operations | Flags, canary, runbooks, on-call | ORCH §13; E00 §18 |

## 2.2 RACI (summary)

| Role | Accountable for |
|------|-----------------|
| Head of Research Engineering | WS01, WS03, WS11, WS12, ORCH |
| Head of Quant Research | WS04, WS05, WS09 gates |
| Portfolio Construction Lead | WS06, WS10 |
| Frontend Lead | WS07 |
| CIO Desk | WS08 acceptance, promotion votes |
| Head of Risk | E14 gates, promote veto |

## 2.3 Spec → workstream map

| Spec | Primary WS | Supporting WS |
|------|------------|---------------|
| E00 | WS01/WS12 | all |
| ORCH | WS01/WS11/WS12 | WS02–WS06 |
| E01 | WS04 | WS02/WS03/WS07 |
| E02 | WS04 | WS03/WS07 |
| E03 | WS04 | WS01 (dual-write), WS07 |
| E04/E05/E08/E09/E11/E13 | WS04 | WS03/WS05/WS07 |
| E14 | WS04 | WS06/WS08/WS12 |
| L4 | WS05 | WS04/WS07/WS09 |
| E10 | WS06 | WS05/WS10/WS07 |

---

# 3. Implementation Phases

| Phase | Name | Exit criteria |
|-------|------|---------------|
| **P0** | Infrastructure | ORCH skeleton, contracts CI, Feature Registry v0, data stage, flags service |
| **P1** | P0 implementations every engine | Each frozen engine emits schema-valid EngineState (even if thin); E03 dual-write path live |
| **P2** | Shadow Mode | L4 shadow writes; specialised engines flaggable; E03 UI unchanged |
| **P3** | Historical Validation | Replay harness; Brier/IC/reliability; walk-forward reports |
| **P4** | Paper Trading | Simulated books from E10; E14 assess; P&L research ledger (no broker) |
| **P5** | Internal CIO | Daily seal + brief for internal roles; promote gates enforced |
| **P6** | Beta Website | `/beta` institutional surfaces SSO/PIN; watermarks |
| **P7** | Production v1 | L4/E10 flags per vote; SLOs green; runbooks |
| **P8** | Institutional Platform | Full voter set Production-capable; warehouse; richer ops; v2 readiness |

Phases overlap by workstream; exit gates are programme-level.

---

# 4. Sprint Plan

**Sprint model:** 2-week engineering sprints · **~52 sprints** (~104 engineer-weeks on critical staffing; **12–18 month** wall-clock with 2–4 engineers in parallel).  
**Effort unit:** engineer-days (1 engineer × 1 day).  
**Duration:** calendar weeks for that sprint box (parallel sprints may share calendar).

---

## Phase 0 — Infrastructure (S01–S06)

### Sprint 01 — Programme bootstrap
| Field | Content |
|-------|---------|
| **Objective** | Stand up IMP tracking + contract repo layout |
| **Deliverables** | `app/contracts/` EngineState JSON Schema; CI schema job; IMP checklist board; package layout per E00 §19 / ORCH §17 |
| **Dependencies** | Frozen specs available |
| **Acceptance** | CI fails invalid EngineState fixture; docs linked from `intelligence-engine/README.md` index |
| **Risk** | Spec PRs not yet merged to main — track via branches until merge |
| **Effort** | 6 eng-days |
| **Duration** | 2 weeks |

### Sprint 02 — ORCH skeleton
| Field | Content |
|-------|---------|
| **Objective** | Minimal scheduler + run ledger |
| **Deliverables** | `orch_runs` / `orch_run_nodes` migrations; `OrchScheduler.trigger`; cron stub `orch_eod_seal`; `/api/v1/orch/status` |
| **Dependencies** | S01 |
| **Acceptance** | Triggered dry-run writes ledger; duplicate trigger lock works |
| **Risk** | Cron host limits on Render |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 03 — Feature flags & auth
| Field | Content |
|-------|---------|
| **Objective** | Cross-engine flag service + admin auth |
| **Deliverables** | `orch_feature_flags` + audit; gateway flag read; PIN/SSO reuse for admin flag console API |
| **Dependencies** | S02 |
| **Acceptance** | Flag flip audited; engines read flags via client only |
| **Risk** | Flag sprawl — enforce ORCH as source of truth |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 04 — L0 staging + L1 validator framework
| Field | Content |
|-------|---------|
| **Objective** | Generic ingest→validate pipeline |
| **Deliverables** | Staging tables; `ValidationReport` writer; critical/non-critical policies; one OHLCV + one macro dataset on-boarded |
| **Dependencies** | S02 |
| **Acceptance** | Critical fail blocks L2 for dataset; report hash stored |
| **Risk** | Vendor flakiness |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 05 — Feature Registry v0
| Field | Content |
|-------|---------|
| **Objective** | Register + materialise first feature set |
| **Deliverables** | Registry tables; builder interface; PIT `as_of`/`available_at`; online cache keys per ORCH §4 |
| **Dependencies** | S04 |
| **Acceptance** | Unregistered feature blocked in Production path unit test |
| **Risk** | Legacy columns bypass registry — add lint ban |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 06 — Observability baseline
| Field | Content |
|-------|---------|
| **Objective** | Metrics/logging for ORCH nodes |
| **Deliverables** | `orch_node_latency_ms`, structured logs, `/orch/health|/ready`, basic dashboard panel |
| **Dependencies** | S02 |
| **Acceptance** | EOD dry-run emits latency + status |
| **Risk** | Metric cardinality |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

**Phase 0 exit:** ORCH dry-run + Feature Registry v0 + flags + L0/L1 sample path green.

---

## Phase 1 — P0 engines (S07–S22)

### Sprint 07 — E01 P0 Macro state
| Field | Content |
|-------|---------|
| **Objective** | First schema-valid `E01State` |
| **Deliverables** | Core axes subset; persist `e01_regime_current`; `GET /e01/state`; ORCH node `E01_MACRO` |
| **Dependencies** | S05 |
| **Acceptance** | Warm GET <300ms; missing data → degraded not fabricated |
| **Risk** | Print latency |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 08 — E14 P0 Firm prior + assess stub
| Field | Content |
|-------|---------|
| **Objective** | Mandatory risk overlay skeleton |
| **Deliverables** | `E14State` prior; `E14Assessment` API stub; fail-closed promote middleware |
| **Dependencies** | S07 |
| **Acceptance** | Promote without assess → `ORCH_E14_REQUIRED` |
| **Risk** | Over-blocking research GET — separate paths |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 09 — E03 contractisation + dual-write
| Field | Content |
|-------|---------|
| **Objective** | Wrap production tech score as `SM_AGI_TECH` EngineState |
| **Deliverables** | Dual-write to `e03_*` tables; shim for `agi_research_score`; parity tests |
| **Dependencies** | S05; existing research engine |
| **Acceptance** | Parity vs legacy scores on fixture universe; UI unchanged |
| **Risk** | Drift in float/order — lock fixtures |
| **Effort** | 14 eng-days |
| **Duration** | 2 weeks |

### Sprint 10 — E02 P0 Factor exposures
| Field | Content |
|-------|---------|
| **Objective** | Minimal factor panel + exposures |
| **Deliverables** | Core factors (mkt/size/value/mom subset); `E02Exposure`; ORCH node |
| **Dependencies** | S07 |
| **Acceptance** | Schema-valid; E03 can optionally residualise |
| **Risk** | Fundamental PIT gaps |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 11 — E13 P0 Fundamental score
| Field | Content |
|-------|---------|
| **Objective** | Thin fundamental attractiveness |
| **Deliverables** | Quality/value subset; `E13Fundamental`; flag default off for UI |
| **Dependencies** | S05 fundamentals features |
| **Acceptance** | PIT join test; EngineState valid |
| **Risk** | Vendor estimate coverage |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 12 — E05 P0 Event calendar bridge
| Field | Content |
|-------|---------|
| **Objective** | Calendar + earnings window state |
| **Deliverables** | Finnhub/calendar ingest; `E05State` for earnings subset; cron slots |
| **Dependencies** | S04 |
| **Acceptance** | PIT event dates; no lookahead test |
| **Risk** | Calendar quality |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 13 — E09 P0 CTA trend
| Field | Content |
|-------|---------|
| **Objective** | TSMOM panel P0 (not E03 technicals) |
| **Deliverables** | Instrument trend scores; `E09State`; flag off |
| **Dependencies** | S05 prices; S07 |
| **Acceptance** | Distinct from E03 outputs; schema-valid |
| **Risk** | Confusion with E03 — naming/docs in UI watermark |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 14 — E08 P0 Vol intelligence
| Field | Content |
|-------|---------|
| **Objective** | RV/IV features without unsafe GEX claims |
| **Deliverables** | Vol regime subset; assumption_set registry; `E08State` |
| **Dependencies** | S04 chains/prices as available |
| **Acceptance** | Missing chain → module off not silent GEX |
| **Risk** | Options data licensing |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 15 — E04 P0 Stat-arb skeleton
| Field | Content |
|-------|---------|
| **Objective** | Pair graph + residual zscore research |
| **Deliverables** | Weekly graph job; `E04State` top pairs; E01 crisis disable |
| **Dependencies** | S07, S09 |
| **Acceptance** | Crisis fixture disables MR; schema-valid |
| **Risk** | Multiple testing — keep Experimental |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 16 — E11 P0 Sentiment soft voter
| Field | Content |
|-------|---------|
| **Objective** | News sentiment features + soft state |
| **Deliverables** | Entity map subset; `E11State`; social ≤5% production weight rule encoded |
| **Dependencies** | S04 news; S05 |
| **Acceptance** | Soft voter absent ⇒ L4 weight 0 path tested |
| **Risk** | NLP cost/latency |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 17 — Weight Registry service
| Field | Content |
|-------|---------|
| **Objective** | E00 §12 dynamic weights runtime |
| **Deliverables** | `weight_registry` tables; load-by-condition API; ban silent prod hardcodes (lint) |
| **Dependencies** | S03 |
| **Acceptance** | E03/L4/E10 read weights by `weight_set_id` |
| **Risk** | Condition explosion — start regime×horizon |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 18 — E14 enrichment + playbooks
| Field | Content |
|-------|---------|
| **Objective** | Crowding/liquidity/corr subset + gates |
| **Deliverables** | Gate catalogue wired; size_mult/conf_adj; midday refresh job |
| **Dependencies** | S08, S10 |
| **Acceptance** | Hard derisk fixture blocks promote |
| **Risk** | False positives — tune Research first |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 19 — ORCH critical path wiring
| Field | Content |
|-------|---------|
| **Objective** | Real EOD DAG E01→E14→E02→E03∥E13→barrier |
| **Deliverables** | `orch-1.0.0.json` edges; barriers; timeouts; snapshot stub |
| **Dependencies** | S07–S11, S02 |
| **Acceptance** | Weekday dry EOD produces snapshot hashes E01/E03/E14 |
| **Risk** | Runtime overruns — shed specialised |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 20 — Engine API hardening
| Field | Content |
|-------|---------|
| **Objective** | Uniform `/api/v1/e0x/*` errors/cache/auth |
| **Deliverables** | Shared error envelope; Cache-Control 60–120s; pagination where needed |
| **Dependencies** | S07–S16 |
| **Acceptance** | Contract tests all P0 engines |
| **Risk** | Gateway/engine split drift |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 21 — P0 completeness audit
| Field | Content |
|-------|---------|
| **Objective** | Close gaps vs “P0 every engine” |
| **Deliverables** | Gap list closed or waived with flag; fixture pack per engine |
| **Dependencies** | S07–S20 |
| **Acceptance** | Checklist signed by Quant Eng + Risk |
| **Risk** | Scope creep into P1 features — reject |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 22 — Phase 1 exit hardening
| Field | Content |
|-------|---------|
| **Objective** | Stability week |
| **Deliverables** | Bug bash; on-call runbook draft; perf smoke |
| **Dependencies** | S21 |
| **Acceptance** | 5 consecutive EOD seals without critical block |
| **Risk** | Vendor outages — degraded paths must hold |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

**Phase 1 exit:** All frozen engines emit EngineState P0; E03 Production unchanged; ORCH EOD seal live.

---

## Phase 2 — Shadow Mode (S23–S28)

### Sprint 23 — L4 P0 ingest + gates
| Field | Content |
|-------|---------|
| **Objective** | L4 consumes E01/E03/E13/E14 |
| **Deliverables** | Adapters; hierarchy gates; naive weighted vote; `L4Opinion` schema |
| **Dependencies** | Phase 1 exit; Weight Registry |
| **Acceptance** | Missing E14 on promote blocked; E03 UI unchanged |
| **Risk** | Over-coupling to incomplete voters |
| **Effort** | 14 eng-days |
| **Duration** | 2 weeks |

### Sprint 24 — L4 shadow write path
| Field | Content |
|-------|---------|
| **Objective** | Persist shadow opinions + comparison |
| **Deliverables** | `l4_shadow_*` tables; `l4_shadow_seal` job; flags per L4 §15 |
| **Dependencies** | S23 |
| **Acceptance** | Shadow rows without mutating E03 tables |
| **Risk** | Storage growth |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 25 — L4 explanation engine
| Field | Content |
|-------|---------|
| **Objective** | Institutional WHY tree |
| **Deliverables** | Contributing/conflicting engines; evidence refs; API |
| **Dependencies** | S23 |
| **Acceptance** | Every opinion has non-empty explanation on success |
| **Risk** | LLM polish leaking claims — keep off |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 26 — Specialised voters into L4
| Field | Content |
|-------|---------|
| **Objective** | Add E05/E09/E08/E11/E04 optional voters |
| **Deliverables** | Agreement matrix API; missing → weight 0 |
| **Dependencies** | S24; engine P0s |
| **Acceptance** | Chaos: kill E11 → L4 still writes |
| **Risk** | Noisy voters — keep Experimental weights low |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 27 — E10 P0 from E03 views
| Field | Content |
|-------|---------|
| **Objective** | Illustrative portfolio from E03 (migration source) |
| **Deliverables** | Constrained optimiser subset; E14 book assess; UI flag off |
| **Dependencies** | S18, S09 |
| **Acceptance** | Infeasible → repair≤3; never drop E14 caps |
| **Risk** | Users read as advice — watermark research |
| **Effort** | 14 eng-days |
| **Duration** | 2 weeks |

### Sprint 28 — Shadow ops console
| Field | Content |
|-------|---------|
| **Objective** | Internal pipeline + shadow divergence UI |
| **Deliverables** | ORCH board; L4 vs E03 panel (internal) |
| **Dependencies** | S24, S06 |
| **Acceptance** | Ops can see blocked reasons + divergence |
| **Risk** | Exposing internal to public — auth gate |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

**Phase 2 exit:** L4 shadow daily; E10 candidate behind flag; E03 primary intact.

---

## Phase 3 — Historical Validation (S29–S34)

### Sprint 29 — Replay harness
| Field | Content |
|-------|---------|
| **Objective** | PIT replay runner |
| **Deliverables** | `run_kind=replay`; `*_replay` schema; snapshot compare |
| **Dependencies** | ORCH snapshots; Feature PIT |
| **Acceptance** | Future join fixtures fail closed |
| **Risk** | Incomplete history |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 30 — Labels + IC/Brier service
| Field | Content |
|-------|---------|
| **Objective** | Standard validation metrics |
| **Deliverables** | Forward residual labels; Rank IC; Brier; job reports |
| **Dependencies** | S29 |
| **Acceptance** | Metrics for E03 + L4 shadow on ≥1 year if data allows |
| **Risk** | Short sample — document limits |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 31 — Calibration & reliability diagrams
| Field | Content |
|-------|---------|
| **Objective** | L4 probability calibration |
| **Deliverables** | Temperature/Platt fit offline; reliability plots; `calibration_id` |
| **Dependencies** | S30, S24 |
| **Acceptance** | Calibration artifact versioned; hot path loads by id |
| **Risk** | Overfit calibration — walk-forward only |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 32 — Walk-forward automation
| Field | Content |
|-------|---------|
| **Objective** | Expanding window + embargo |
| **Deliverables** | WF orchestrator; report pack per engine |
| **Dependencies** | S29–S31 |
| **Acceptance** | Embargo respected in tests |
| **Risk** | Compute cost |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 33 — Engine calibration gates wiring
| Field | Content |
|-------|---------|
| **Objective** | Encode §10 gates in CI/CD promote checklist |
| **Deliverables** | Machine-readable gate report; block flag flips if fail |
| **Dependencies** | S30–S32 |
| **Acceptance** | Cannot set Production flag without gate artifact |
| **Risk** | Process override — require dual ACK |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 34 — Validation review week
| Field | Content |
|-------|---------|
| **Objective** | Quant sign-off on shadow KPIs |
| **Deliverables** | Written review; go/no-go for Internal CIO |
| **Dependencies** | S33 |
| **Acceptance** | CIO + Quant + Risk signatures |
| **Risk** | Underperformance → extend shadow, do not promote |
| **Effort** | 6 eng-days |
| **Duration** | 2 weeks |

**Phase 3 exit:** Replay+WF+calibration operational; promote checklist enforced.

---

## Phase 4 — Paper Trading (S35–S38)

### Sprint 35 — Paper book ledger
| Field | Content |
|-------|---------|
| **Objective** | Simulated positions from E10 recommendations |
| **Deliverables** | `paper_books`, fills at next open/close rules; no broker API |
| **Dependencies** | S27 |
| **Acceptance** | Research disclaimer; immutable fill log |
| **Risk** | Mistaken for live trading — naming + auth |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 36 — TCA & costs research
| Field | Content |
|-------|---------|
| **Objective** | Apply cost models to paper P&L |
| **Deliverables** | Spread/ADV cost engine; turnover reports |
| **Dependencies** | S35 |
| **Acceptance** | Gross vs net P&L visible |
| **Risk** | Optimistic costs — use conservative defaults |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 37 — E14 continuous assess on paper books
| Field | Content |
|-------|---------|
| **Objective** | Risk overlay on simulated books |
| **Deliverables** | Daily assess; breach alerts |
| **Dependencies** | S35, S18 |
| **Acceptance** | Hard cap breaches logged + weights clipped in sim |
| **Risk** | Alert fatigue |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 38 — Paper vs benchmark pack
| Field | Content |
|-------|---------|
| **Objective** | Benchmark comparison research |
| **Deliverables** | Excess return vs Nifty500/sector; drawdown stats |
| **Dependencies** | S36 |
| **Acceptance** | Report generated weekly |
| **Risk** | Short track record — watermark |
| **Effort** | 6 eng-days |
| **Duration** | 2 weeks |

**Phase 4 exit:** Paper loop running; still research-only.

---

## Phase 5 — Internal CIO (S39–S42)

### Sprint 39 — L6 CIO brief assembler
| Field | Content |
|-------|---------|
| **Objective** | Structured daily brief from snapshots |
| **Deliverables** | Brief JSON + markdown; claim-bound; LLM polish flag off by default |
| **Dependencies** | S19 snapshots; S25 explanations; E14 |
| **Acceptance** | Brief blocked if E14 seal missing |
| **Risk** | Narrative drift — structured sections mandatory |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 40 — Internal CIO desk UI
| Field | Content |
|-------|---------|
| **Objective** | Authenticated internal desk |
| **Deliverables** | Regime, risk, E03 ranks, L4 shadow, conflicts, snapshot timeline |
| **Dependencies** | S28, S39 |
| **Acceptance** | Role-gated; Experimental labels visible |
| **Risk** | Information overload — hierarchy per L4 UI |
| **Effort** | 12 eng-days |
| **Duration** | 2 weeks |

### Sprint 41 — Promotion workflow
| Field | Content |
|-------|---------|
| **Objective** | Human-in-loop promote to publish candidates |
| **Deliverables** | Promote request → E14 assess → ACK; audit |
| **Dependencies** | S08, S33 |
| **Acceptance** | Dual control Risk+CIO for client-bound |
| **Risk** | Bottleneck — batch promote tools |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 42 — Internal SLO soak
| Field | Content |
|-------|---------|
| **Objective** | Operate as internal product |
| **Deliverables** | 20 consecutive IST seals; incident log empty of Sev-1 |
| **Dependencies** | S39–S41 |
| **Acceptance** | Availability/latency SLOs met (§14) |
| **Risk** | Holiday calendars |
| **Effort** | 6 eng-days |
| **Duration** | 2 weeks |

**Phase 5 exit:** Internal CIO daily use; promotion workflow live.

---

## Phase 6 — Beta Website (S43–S46)

### Sprint 43 — Beta shell & watermarks
| Field | Content |
|-------|---------|
| **Objective** | `/beta` institutional shell |
| **Deliverables** | Routing, auth, SHADOW/RESEARCH watermarks, disclaimer components |
| **Dependencies** | Existing PIN/auth patterns |
| **Acceptance** | Experimental never on unmarked public |
| **Risk** | SEO indexing — noindex |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 44 — Engine beta pages (core)
| Field | Content |
|-------|---------|
| **Objective** | E01/E03/E14/L4 shadow pages |
| **Deliverables** | Gauges, evidence tree, agreement matrix widgets |
| **Dependencies** | S43, engine APIs |
| **Acceptance** | E00 §15 required views for these surfaces |
| **Risk** | Perf on mobile — budget widgets |
| **Effort** | 14 eng-days |
| **Duration** | 2 weeks |

### Sprint 45 — Portfolio + paper beta
| Field | Content |
|-------|---------|
| **Objective** | E10 + paper research views |
| **Deliverables** | Weights, constraints, breaches, paper P&L |
| **Dependencies** | S27, S35, S43 |
| **Acceptance** | No BUY/SELL buttons; research CTAs only |
| **Risk** | UX misread as brokerage |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 46 — Beta hardening
| Field | Content |
|-------|---------|
| **Objective** | Security/perf/a11y pass |
| **Deliverables** | Rate limits; cache; load test; feedback channel |
| **Dependencies** | S44–S45 |
| **Acceptance** | p95 warm API <300ms on core GETs |
| **Risk** | Data leaks via verbose errors — sanitize |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

**Phase 6 exit:** Closed beta usable; watermarks correct.

---

## Phase 7 — Production v1 (S47–S50)

### Sprint 47 — Production readiness review
| Field | Content |
|-------|---------|
| **Objective** | Go/no-go pack |
| **Deliverables** | SLO board, gate artifacts, rollback drills, DR notes |
| **Dependencies** | Phases 3–6 |
| **Acceptance** | Written approvals Eng/Quant/Risk/CIO |
| **Risk** | Premature L4 primary — default keep E03 primary if gates marginal |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 48 — Canary & rollback automation
| Field | Content |
|-------|---------|
| **Objective** | ORCH canary percent + one-click flag rollback |
| **Deliverables** | Canary router; rollback runbook automated |
| **Dependencies** | S03, S47 |
| **Acceptance** | Rollback RTO ≤15m flag-only drill passed |
| **Risk** | Split-brain currents — EOD stays shadow-compare |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

### Sprint 49 — Production cutover (conservative)
| Field | Content |
|-------|---------|
| **Objective** | Production v1 surfaces |
| **Deliverables** | Production flags for ORCH/E01/E14/E03 contracts; L4 primary **only if** superiority vote passes else remain shadow; E10 optional |
| **Dependencies** | S47–S48 |
| **Acceptance** | Public research stable; monitoring green 10 sessions |
| **Risk** | User confusion on dual scores — UX copy |
| **Effort** | 10 eng-days |
| **Duration** | 2 weeks |

### Sprint 50 — Production hypercare
| Field | Content |
|-------|---------|
| **Objective** | Stabilize v1 |
| **Deliverables** | Sev playbooks; performance patches; postmortem template |
| **Dependencies** | S49 |
| **Acceptance** | No open Sev-1; backlog groomed for P8 |
| **Risk** | Alert noise |
| **Effort** | 8 eng-days |
| **Duration** | 2 weeks |

**Phase 7 exit:** **Production v1** live under frozen architecture; L4 promotion conditional.

---

## Phase 8 — Institutional Platform (S51–S52+)

### Sprint 51 — Full voter Production track
| Field | Content |
|-------|---------|
| **Objective** | Promote specialised engines that pass gates |
| **Deliverables** | E05/E13/E09/E08/E04/E11 Candidate→Production per gate packs |
| **Dependencies** | Phase 3 gates per engine |
| **Acceptance** | Each engine §10 pack signed |
| **Risk** | Parallel promotions — stagger |
| **Effort** | 16 eng-days |
| **Duration** | 2 weeks |

### Sprint 52 — Warehouse & institutional ops
| Field | Content |
|-------|---------|
| **Objective** | Longer retention, richer L8, E10 multi-sleeve |
| **Deliverables** | Warehouse export; advanced monitoring; multi-sleeve E10; institutional API keys |
| **Dependencies** | S49 |
| **Acceptance** | 5y retention policy enforced; institutional SLO dashboard |
| **Risk** | Cost — tier storage |
| **Effort** | 14 eng-days |
| **Duration** | 2 weeks |

**Post-S52:** Continuous improvement under E00 governance only (no silent redesign). E06/E07/E12 remain Experimental until amended registry + annex.

---

## 4.1 Sprint summary table

| Sprint | Phase | Objective (short) | Effort (d) | Duration (w) |
|--------|-------|-------------------|------------|--------------|
| 01 | 0 | Bootstrap/contracts CI | 6 | 2 |
| 02 | 0 | ORCH skeleton | 10 | 2 |
| 03 | 0 | Flags/auth | 8 | 2 |
| 04 | 0 | L0/L1 framework | 12 | 2 |
| 05 | 0 | Feature Registry v0 | 12 | 2 |
| 06 | 0 | Observability baseline | 8 | 2 |
| 07 | 1 | E01 P0 | 12 | 2 |
| 08 | 1 | E14 P0 | 12 | 2 |
| 09 | 1 | E03 dual-write | 14 | 2 |
| 10 | 1 | E02 P0 | 12 | 2 |
| 11 | 1 | E13 P0 | 12 | 2 |
| 12 | 1 | E05 P0 | 10 | 2 |
| 13 | 1 | E09 P0 | 10 | 2 |
| 14 | 1 | E08 P0 | 12 | 2 |
| 15 | 1 | E04 P0 | 12 | 2 |
| 16 | 1 | E11 P0 | 12 | 2 |
| 17 | 1 | Weight Registry | 10 | 2 |
| 18 | 1 | E14 enrichment | 12 | 2 |
| 19 | 1 | ORCH critical path | 10 | 2 |
| 20 | 1 | API hardening | 8 | 2 |
| 21 | 1 | P0 audit | 8 | 2 |
| 22 | 1 | Phase 1 harden | 8 | 2 |
| 23 | 2 | L4 P0 gates | 14 | 2 |
| 24 | 2 | L4 shadow write | 10 | 2 |
| 25 | 2 | L4 explanations | 10 | 2 |
| 26 | 2 | L4 full voters | 12 | 2 |
| 27 | 2 | E10 P0 | 14 | 2 |
| 28 | 2 | Shadow ops UI | 8 | 2 |
| 29 | 3 | Replay harness | 12 | 2 |
| 30 | 3 | IC/Brier | 10 | 2 |
| 31 | 3 | Calibration | 10 | 2 |
| 32 | 3 | Walk-forward | 10 | 2 |
| 33 | 3 | Gate wiring | 8 | 2 |
| 34 | 3 | Validation review | 6 | 2 |
| 35 | 4 | Paper ledger | 12 | 2 |
| 36 | 4 | TCA costs | 8 | 2 |
| 37 | 4 | Paper E14 | 8 | 2 |
| 38 | 4 | Benchmark pack | 6 | 2 |
| 39 | 5 | CIO brief | 12 | 2 |
| 40 | 5 | Internal desk UI | 12 | 2 |
| 41 | 5 | Promote workflow | 8 | 2 |
| 42 | 5 | Internal soak | 6 | 2 |
| 43 | 6 | Beta shell | 8 | 2 |
| 44 | 6 | Core beta pages | 14 | 2 |
| 45 | 6 | Portfolio/paper beta | 10 | 2 |
| 46 | 6 | Beta harden | 8 | 2 |
| 47 | 7 | Prod readiness | 8 | 2 |
| 48 | 7 | Canary/rollback | 8 | 2 |
| 49 | 7 | Prod cutover | 10 | 2 |
| 50 | 7 | Hypercare | 8 | 2 |
| 51 | 8 | Voter promotions | 16 | 2 |
| 52 | 8 | Warehouse/ops v2 | 14 | 2 |

**Total effort (serial sum):** ~526 engineer-days ≈ **26 engineer-months**.  
**Wall-clock with 3 engineers parallelizing WS02–WS07:** target **12–18 months** to Production v1 (S49), Institutional enrichment through S52+.

---

# 5. Repository Roadmap

## 5.1 Backend modules

```
intelligence-engine/app/
  contracts/           # JSON Schemas (WS01)
  features/            # Builders + registry client (WS03)
  orch/                # Scheduler/executor (WS01/WS12)
  engines/
    e01/ e02/ e03/ e04/ e05/ e08/ e09/ e11/ e13/ e14/
  l4/                  # Composite (WS05)
  e10/                 # Portfolio (WS06)
  validation/          # IC/Brier/calibration (WS09)
  paper/               # Paper trading (WS10)
  research_gen/        # CIO brief (WS08)
  clients/             # Typed EngineState clients

server/
  services/            # Node gateway proxies
  jobs/                # Cron entrypoints → ORCH
  scripts/             # Legacy research engine (E03 compat)
```

## 5.2 Frontend modules

```
src/pages/beta/        # Beta institutional shell
src/pages/cio/         # Internal CIO desk
src/widgets/engines/   # Per-engine widgets
src/widgets/l4/        # Gauges, evidence tree, matrix
src/widgets/orch/      # Pipeline board
src/widgets/portfolio/ # E10 + paper
src/components/research/ # Disclaimers/watermarks
```

## 5.3 Shared libraries

| Lib | Purpose |
|-----|---------|
| `@agi/contracts` or `app/contracts` | Schemas + pydantic/zod models |
| `app/common/conf` | conf-1.0 helpers |
| `app/common/hashing` | input_hash/output_hash |
| `app/common/pit` | as_of joins |
| Gateway error middleware | E00 §14 envelope |

## 5.4 Workers & schedulers

| Worker | Role |
|--------|------|
| `orch-worker-batch` | EOD/intraday DAG nodes |
| `orch-worker-interactive` | Symbol recompute |
| `orch-worker-replay` | WF/replay |
| `legacy-research-worker` | E03 tech until full cutover |
| Render cron / equivalent | Thin triggers only |

## 5.5 Database migrations order

1. ORCH ledger/flags/DAG  
2. Feature registry + PIT  
3. E01/E14/E03  
4. E02/E13  
5. Specialised engines  
6. L4 shadow  
7. E10 + paper  
8. Validation/calibration artifacts  
9. Warehouse export helpers  

All migrations expandable/backward-compatible per E00 §13.

---

# 6. Database Roadmap

## 6.1 Table groups

| Group | Examples |
|-------|----------|
| ORCH | `orch_runs`, `orch_run_nodes`, `orch_snapshots`, `orch_feature_flags`, `orch_dag_*` |
| Registry | `feature_registry`, `signal_registry`, `weight_registry` |
| Engine current/history | `e01_regime_current`, `e03_alpha_*`, `e14_risk_current`, `l4_opinion_current`, … |
| Shadow | `l4_shadow_comparison` |
| Portfolio/paper | `e10_portfolios`, `paper_books`, `paper_fills` |
| Validation | `validation_reports`, `calibration_artifacts`, `wf_reports` |
| Evidence | `orch_evidence_edges` |

## 6.2 Indexes (minimum)

- `(as_of, symbol)` on all universe score tables  
- `(snapshot_id)` / `(run_id)` on orch  
- `(object_hash)` on E14 assessments  
- BRIN/time indexes on history tables  

## 6.3 Time-series & warehouse

| Store | Use | Horizon |
|-------|-----|---------|
| OLTP Postgres | Currents + recent history | Hot 90d |
| PIT warehouse schema | Features/scores by as_of | ≥5y Production |
| Object/blob | Chains, NLP docs | Per license |
| Export warehouse (P8) | Analytics | Tiered cold |

## 6.4 Caching

| Tier | TTL |
|------|-----|
| Online features | 5–60m |
| API GET current | 60–120s |
| Negative cache | 30–120s |
| CDN (public) | short + purge on seal |

---

# 7. API Roadmap

## 7.1 Implementation order

1. `/orch/*` status/flags/runs  
2. `/e01/state`, `/e14/*`  
3. `/e03/*` (+ legacy shim)  
4. `/e02`, `/e13`  
5. specialised `/e0x`  
6. `/l4/opinion` (shadow)  
7. `/e10/*`  
8. `/paper/*`  
9. `/validation/*`  
10. `/research/cio-brief`  

## 7.2 Versioning

- Prefix `/api/v1/` only until breaking change → `/api/v2/`  
- Engine `version` / `model_version` inside payloads independent of URL version  

## 7.3 Security

| Surface | Auth |
|---------|------|
| Public research | Existing site rules + no Experimental |
| Beta | PIN/SSO |
| Internal CIO / ORCH admin | Role-gated SSO + audit |
| Promote / flag flips | Dual control |

Secrets only in server env (E00 §2.1).

## 7.4 Caching & rate limits

| Class | Cache | Rate limit (start) |
|-------|-------|--------------------|
| Current state GET | 60–120s | 60/min/IP user |
| Interactive recompute | no-store | 10/min/user |
| Admin triggers | no-store | 5/min/admin |
| Validation exports | 5m | 10/hour/user |

---

# 8. Frontend Roadmap

## 8.1 Dashboard order

1. Ops / ORCH pipeline (internal)  
2. E01 Macro  
3. E14 Risk  
4. E03 XS / technical research (Production)  
5. L4 shadow desk  
6. E13 / E02  
7. Specialised (E05→E09→E08→E04→E11)  
8. E10 Portfolio  
9. Paper trading  
10. CIO brief reader  
11. Validation/calibration admin  

## 8.2 Widgets (shared)

- Probability gauges (L4)  
- Evidence tree  
- Engine agreement matrix  
- Confidence decomposition  
- Regime chips (from E01 state, not decorative)  
- Risk gate banner (E14)  
- Snapshot timeline  
- Heatmaps (sector × score)  
- Rank tables with PIT as_of  

## 8.3 Charts / heatmaps

- Factor exposure bars (E02)  
- IC time series (validation)  
- Reliability diagrams  
- Vol term (E08 when live)  
- Paper equity curve  

## 8.4 Admin / monitoring

- Flag console (audited)  
- Pipeline board  
- Dead-letter / blocked reasons  
- SLO burn  

**UI law:** no BUY/SELL; watermarks for non-Production; preserve AGI design system where present.

---

# 9. Backtesting Roadmap

| Capability | Sprint anchor | Notes |
|------------|---------------|-------|
| Historical replay | S29 | ORCH `replay` + PIT |
| Walk-forward | S32 | Expanding + embargo |
| Transaction costs | S36 | Paper + research BT |
| Universe construction | S05/S09 | Membership as_of |
| Benchmark comparison | S38 | Nifty500 / sector |
| Stress scenarios | S18/S37 | E14 library |
| Superiority tests L4 vs E03 | S30–S34 | Promotion input |

Backtests never look ahead; CI owns PIT violation tests.

---

# 10. Validation Gates

**No engine reaches Production flags without all gates green** (E00 §16–§18; L4 §15; ORCH §12).

| Gate | Requirement |
|------|-------------|
| Unit tests | Core formulas/contracts ≥ critical paths |
| Integration tests | ORCH node + DB + API |
| Replay tests | PIT fixtures stable |
| Calibration tests | Reliability/Brier where probabilistic |
| Performance tests | Latency budgets (ORCH §10 / engine specs) |
| Statistical superiority / non-inferiority | Required for displacing incumbent (e.g., L4 vs E03) |
| Risk gate | E14 path proven fail-closed |
| Explainability | Evidence pack present on promote |
| Approval | Quant + Risk (+ CIO if client-facing) |

**Artifacts:** stored as `gate_report_id` referenced by flag audit row.

---

# 11. Feature Flag Plan

Canonical pattern per engine/surface:

| Stage | Flag pattern | Audience |
|-------|--------------|----------|
| Development | `e0x_dev_enabled` | Engineers |
| Shadow | `e0x_shadow_write` | Internal metrics |
| Internal | `e0x_internal_ui` | CIO desk |
| Beta | `e0x_beta_ui` | Beta users |
| Production | `e0x_production` | General research site |
| Rollback | invert Production/Beta; keep shadow writes optional |

### Per-engine defaults at programme start

| Engine/Surface | Dev | Shadow | Internal | Beta | Production | Rollback note |
|----------------|-----|--------|----------|------|------------|---------------|
| ORCH | on | n/a | on | limited status | on (infra) | pin dag_version |
| E01 | on | on | on | on | **target on** | last good regime |
| E14 | on | on | on | on | **on enforce** | never disable enforce on promote |
| E03 | on | dual-write | on | on | **on (incumbent)** | legacy worker |
| E02 | on | on | on | off | off | — |
| E13 | on | on | on | off | off | — |
| E05 | on | on | on | off | off | — |
| E09 | on | on | off | off | off | — |
| E08 | on | on | off | off | off | license-dependent |
| E04 | on | on | off | off | off | — |
| E11 | on | on | off | off | off | social weight cap |
| L4 | on | **on** | on | watermark | **off until vote** | `l4_replace_e03_display=false` |
| E10 | on | on | on | watermark | off | views_source=e03 |
| Paper | on | n/a | on | watermark | off | — |
| LLM polish | off | off | opt-in | off | off | claim-bound only |

---

# 12. Risk Register

| ID | Class | Risk | Likelihood | Impact | Mitigation |
|----|-------|------|------------|--------|------------|
| R1 | Technical | ORCH becomes bottleneck monolith | M | H | Keep thin; contracts first; extract later per ORCH §14 |
| R2 | Technical | E03 dual-write drift | M | H | Parity fixtures; block cutover on fail |
| R3 | Data | Vendor outage / delayed prints | H | M | Degraded modes; multi-source fallbacks; stale flags |
| R4 | Data | Options/alt-data licensing gaps | H | M | Module flags; E08/E11 optional voters |
| R5 | Model | L4 underperforms E03 | M | H | Stay shadow; no primary flip |
| R6 | Model | Overfitting calibration | M | H | Walk-forward only; embargo |
| R7 | Operational | On-call burnout / alert noise | M | M | SLO-based paging; runbooks S50 |
| R8 | Operational | Flag mis-flip exposes Experimental | L | H | Dual control; CI gate artifacts |
| R9 | Compliance | UI read as investment advice / execution | M | H | Research-only copy; no order buttons; legal review |
| R10 | Compliance | PIT / look-ahead scandal | L | H | Replay CI; fail closed |
| R11 | Scaling | EOD over runtime budget | M | M | Critical-path shed; shard universe |
| R12 | Scaling | Storage cost 5y PIT | M | M | Tiered warehouse P8 |
| R13 | Programme | Spec PRs unmerged blocking main | H | M | Merge architecture PRs early in S01–S02 |
| R14 | Programme | Scope creep redesign | M | H | IMP rejects architecture changes without E00 amendment |

---

# 13. Resource Planning

## 13.1 Engineering effort

| Role | Allocation (steady) | Focus |
|------|---------------------|-------|
| Research platform eng | 1.0–1.5 FTE | WS01/03/11/12 |
| Quant eng | 1.0–1.5 FTE | WS04/05/09 |
| Full-stack / frontend | 0.5–1.0 FTE | WS07/08 |
| Part-time Quant research | 0.25–0.5 FTE | gates, weights |
| Risk/CIO review | 0.15 FTE | promotions |

**~526 eng-days** planned work ⇒ with **3 FTE** ≈ **8–10 months** dense execution + buffer ⇒ **12–18 months** including validation soaks and hypercare.

## 13.2 Infrastructure

| Component | Plan |
|-----------|------|
| App host (Render or equiv.) | Web + 2–3 workers |
| Postgres (Supabase/prod) | Primary OLTP + PIT schema |
| Redis | Online features + locks |
| Object storage | Chains/docs |
| CI | GitHub Actions |

## 13.3 Storage / compute / GPU

| Resource | P0–P2 | P3–P7 | P8 |
|----------|-------|-------|----|
| DB storage | 50–100GB | 200–500GB | 1TB+ tiered |
| Worker RAM | 4–8GB | 8–16GB | autoscaled |
| GPU | none required | optional E11/E12 | Ray/GPU lab optional |
| Replay compute | low | burst monthly | scheduled cluster |

## 13.4 Monthly operating cost (indicative bands)

| Band | Monthly USD (indicative) | When |
|------|--------------------------|------|
| Lean | $200–600 | Phase 0–2 single env |
| Standard | $800–2,000 | Phase 3–6 staging+prod+Redis |
| Institutional | $2,000–6,000+ | Phase 7–8 warehouse, more workers, vendor fees extra |

**Vendor data licenses** (options, estimates, alt-data) are **additive** and may dominate — budget separately per procurement.

---

# 14. Success Metrics

## 14.1 Platform SLOs

| Metric | Target |
|--------|--------|
| Warm GET p95 (core state APIs) | < 300ms |
| EOD critical path seal | ≤ 19:30 IST |
| ORCH availability (scheduler) | ≥ 99.5% weekdays |
| E14 promote enforce | 100% |
| PIT CI | 0 tolerated violations on Production paths |
| Snapshot seal success | ≥ 95% weekdays (ex-holidays) |

## 14.2 Coverage

| Metric | Target (Prod v1) |
|--------|------------------|
| Universe score coverage E03 | ≥ 95% eligible |
| E01 weekday freshness | < 6h stale ratio policy |
| L4 shadow coverage | ≥ 90% of E03 scored names |

## 14.3 Prediction / calibration

| Metric | Target |
|--------|--------|
| E03 Rank IC | Document baseline; monitor decay |
| L4 Brier / reliability | Non-inferior before primary |
| Calibration slope | Investigated if ≪ 1 |
| Gate integrity | 100% on promotes |

## 14.4 Backtest / paper quality

| Metric | Target |
|--------|--------|
| Replay PIT pass rate | 100% on release suite |
| Paper net vs gross | Costs applied; no hidden optimism |
| Drawdown reporting | Always with paper results |

## 14.5 Product

| Metric | Target |
|--------|--------|
| Internal CIO daily adoption | Brief opened ≥4/5 sessions after P5 |
| Beta feedback loop | Triaged weekly |
| Sev-1 reopen after rollback drill | 0 open |

---

# 15. Release Timeline

Realistic milestone plan on a **12–18 month** wall-clock (3-FTE class team). Dates are programme targets, not architecture changes.

| Milestone | Marker | Target window | Sprint exit |
|-----------|--------|---------------|-------------|
| **Architecture Complete** | Specs frozen (done) | Complete | — |
| **P0 Infrastructure Complete** | ORCH+Registry+flags | Month 1–2 | S06 |
| **P0 Engines Complete** | All engines EngineState P0 | Month 4–6 | S22 |
| **Shadow Complete** | L4 daily shadow + ops | Month 6–8 | S28 |
| **Historical Validation Complete** | Replay/WF/gates | Month 8–10 | S34 |
| **Paper Trading Live (research)** | Simulated books | Month 10–11 | S38 |
| **Internal CIO Live** | Daily seal+brief | Month 11–13 | S42 |
| **Public Beta** | `/beta` watermarked | Month 12–14 | S46 |
| **Production v1** | Conservative cutover | Month 13–16 | S49–S50 |
| **Institutional v2** | Full voters+warehouse | Month 16–18+ | S51–S52 |

### Sequencing principle

```
Architecture Complete ✓
        ↓
P0 Infrastructure
        ↓
P0 Engines (E01/E14/E03 critical)
        ↓
Shadow (L4)
        ↓
Historical Validation
        ↓
Paper Trading
        ↓
Internal CIO
        ↓
Public Beta
        ↓
Production v1
        ↓
Institutional Platform v2
```

### Explicit non-goals in this programme window

- Broker OMS / live order execution (requires separate Execution Constitution)  
- Architectural redesign of frozen engines  
- Forcing L4 to replace E03 without statistical superiority  
- Production E06/E07/E12 without E00 amendment + ORCH annex  

---

# 16. Operating cadence

| Cadence | Activity |
|---------|----------|
| Daily | ORCH EOD seal; stale/gate review |
| Weekly | Sprint progress vs IMP; risk register |
| Biweekly | Demo internal CIO artifacts |
| Monthly | Validation KPI review; cost review |
| Per promotion | Gate pack + dual ACK |

---

# 17. Document control

| Version | Notes |
|---------|-------|
| 1.0.0 | Initial official execution roadmap under Architecture v1.0 freeze |

Amendments to **this** programme (dates, sprint swaps, staffing) do **not** require E00 amendment.  
Amendments that change architecture, contracts, or engine semantics **do** require E00 governance.

---

*End of IMPLEMENTATION MASTER PROGRAMME V1 — execution roadmap for AGI Investment Office under E00 Architecture v1.0 Feature Freeze*
