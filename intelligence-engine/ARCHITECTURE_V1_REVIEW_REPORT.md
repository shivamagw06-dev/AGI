# ARCHITECTURE V1 REVIEW REPORT  
## Independent Institutional Architecture Audit — AGI Investment Office

**Document ID:** `AVR-V1`  
**Filename:** `ARCHITECTURE_V1_REVIEW_REPORT.md`  
**Audit subject:** Architecture v1.0 Feature Freeze corpus  
**Audit type:** Pre-implementation weakness review (non-redesign)  
**Review board posture:** Bloomberg / Aladdin / Two Sigma / Citadel / RenTech / Bridgewater / Google / Microsoft / Amazon / NASA Flight Software joint committee analogue  
**Status:** Independent audit report  
**Version:** 1.0.0  
**Date:** 2026-07-25  
**Assumption:** Implementation of Architecture v1.0 has **not** yet started as an integrated programme on `main`

### Corpus audited

| Class | Documents |
|-------|-----------|
| Governance | E00 Constitution; ORCH (`L5_ENGINE_INTERACTION_ORCHESTRATION.md`); L4 Composite Intelligence; IMP-V1; PRR-V1 |
| Engines | E01, E02, E03, E04, E05, E08, E09, E10, E11, E13, E14 |
| Explicitly out of redesign scope | No new engines; no L0–L8 redesign; no replacement of E00 authority ladder |

### Audit method

1. Cross-read governance + engine normative claims  
2. Dependency / ordering / failure-policy triangulation (E00 ↔ ORCH ↔ L4 ↔ E10 ↔ E03)  
3. Contract field audit (`EngineState`, conf-1.0, evidence, Weight Registry)  
4. Repository reality check (`main` vs draft branches/PRs)  
5. Pre-production readiness judgment against Internal / Paper / Public / Institutional / Licensed-product bars  

### Non-goals of this report

- Do **not** redesign Architecture v1.0  
- Do **not** invent engines  
- Do **not** replace frozen research math  
- Recommendations limited to clarifications, tests, sequencing, ops — anything structural marked **Requires E00 Amendment**

---

# 1. Executive Assessment

## 1.1 Overall maturity

Architecture v1.0 is a **serious institutional specification set**: layered L0–L8, EngineState law, conf-1.0, evidence packs, authority ladder, Weight Registry, ORCH control plane, L4 fusion with shadow-before-crown, IMP programme, and PRR gates.

Maturity is **high for paper architecture**, **low for executable platform reality**. The corpus is fragmented across unmerged branches; E00 still describes several engines as “spec pending” while those specs already claim freeze; E10/L4/E03 disagree on the portfolio view source of truth.

**Maturity verdict:** Spec-complete in breadth; **not yet configuration-controlled as a single baseline**.

## 1.2 Scorecard (/100)

| Dimension | Score | Board reading |
|-----------|------:|---------------|
| **Architecture score** | **74** | Strong layering and governance ideas; consistency debt and naming hazards reduce score |
| **Engineering score** | **38** | Specs rich; integrated implementation, schema SSOT, and `main` baseline absent |
| **Scalability score** | **62** | ORCH sharding/async path credible for India-univ research; warehouse/GPU deferred; EOD critical path fragile |
| **Maintainability score** | **58** | Many large normative docs + overlapping PIT ownership + dual naming (L5/ORCH) raise long-run cost |
| **Research quality score** | **79** | Excellent institutional intent (PIT, evidence, shadow, E14); contract example drift and double-count risks remain |
| **Operational readiness score** | **45** | ORCH/PRR describe ops well; runbooks/alerts/drills not evidenced because build not started |
| **Institutional readiness score** | **41** | Insufficient for licensed products / external institutional fiduciary use; adequate trajectory for internal research if conditions cleared |

**Composite board index (unweighted mean): 57 / 100** — promising architecture, **not launch-ready**.

## 1.3 One-line assessment

> Architecture v1.0 is **approvable as a research-office blueprint only after mandatory consistency conditions**; it is **not** yet a flight-ready production baseline.

---

# 2. Cross-Document Consistency Review

Findings use IDs **C-*** (consistency). Severity: Blocker / High / Medium / Low.

## 2.1 Naming & terminology

| ID | Sev | Finding |
|----|-----|---------|
| C-N1 | High | **`L5_` filename vs E00 Layer 5.** ORCH file `L5_ENGINE_INTERACTION_ORCHESTRATION.md` documents that it is **not** E00 Layer 5 (E10). Still, E00 signal/consumer language and human speech will say “L5” ambiguously (ORCH vs Portfolio). |
| C-N2 | Medium | **“Voter” overload.** L4 “consumed engines” include E02 as context/leakage, not a directional voter; ORCH consumer matrix treats edges differently. Onboarding risk. |
| C-N3 | Medium | E00 consumer enum text using **“L5”** is ambiguous given ORCH’s L5_ filename. Prefer `E10` / `ORCH` exclusively in implementation docs. |
| C-N4 | Low | Document IDs (`E00`, `ORCH`, `L4`, `IMP-V1`, `PRR-V1`) are clear; filename/ID split for ORCH is the main hazard. |

## 2.2 Contracts & EngineState

| ID | Sev | Finding |
|----|-----|---------|
| C-C1 | **Blocker** | **No schema SSOT on `main`.** E00 points to `app/schemas/` + per-engine `schema.py`; ORCH mandates `contracts/v{N}/...` and `app/orch/contracts/engine_state.schema.json`. Neither integrated baseline exists on `main`; specs live on separate PRs. |
| C-C2 | High | **Confidence shape drift.** E00/`conf-1.0` require `{value, components, method_version}`. Multiple frozen engine examples still show scalar `confidence` or aliases (`factor_confidence`, `fundamental_confidence`, `trend_confidence`). L4/ORCH assume `confidence.value`. |
| C-C3 | High | **Evidence pack drift.** E00 §5/§10 mandate evidence buckets; newer engines (E04/E09 class) closer to compliance; core E01/E02/E03/E13/E14 examples often omit full packs despite E00 success criteria. |
| C-C4 | Medium | **Score envelope drift.** L4 reads `score.normalized_0_100` plus engine-specific fields; several engines omit universal `score{}` and only expose domain fields. |
| C-C5 | Medium | **Weight “hardcode” ambiguity.** E00 bans silent Production hardcodes; L4/E03/E14 publish numeric tables in-spec without always labeling them as **Weight Registry seed JSON**. |

## 2.3 Versioning & freeze claims

| ID | Sev | Finding |
|----|-----|---------|
| C-V1 | **Blocker** | **E00 registry stale vs freeze declaration.** E00 still says E04/E05/E08/E09/E11 **“spec pending”** and §20.1 lists completing those specs as **v1.1**, while programme/freeze statements treat those specs as Architecture v1.0 frozen. |
| C-V2 | High | Engine headers claim **Candidate-track**; E00 promotion rows remain Experimental/Research for several — lifecycle skip risk vs E00 §18. |
| C-V3 | High | **Feature prefix debt.** E09/E04/E11 require `TREND_` / `RVAL_` / `ALT_` prefixes “pending E00 §6 / v1.1” while also declaring normative IDs now — dual standard. |
| C-V4 | Medium | E00 Annex B normative set under-lists **L4** and **ORCH** relative to freeze corpus claimed by IMP/PRR. |

## 2.4 Confidence / evidence / Weight Registry standards

| ID | Sev | Finding |
|----|-----|---------|
| C-S1 | High | Conflict example confidence caps differ: E00 ladder example **≤0.60** vs L4 worked policy **≤0.55** for similar tech-bull/fund-bear/risk-off case. |
| C-S2 | High | L4 ranks E04/E09/E08/E05 inside hierarchy; E00 §11 ladder stops at coarse P0–P4 without those ranks — **two authority narratives**. |
| C-S3 | Medium | Weight Registry service is mandatory in law but only programme-scheduled (IMP S17) — no normative seed files in corpus. |

## 2.5 API & database consistency

| ID | Sev | Finding |
|----|-----|---------|
| C-A1 | Medium | E00 APIs under `/api/intelligence/e{nn}/...`; ORCH documents `/api/v1/orch/...` while citing E00 §14.2 — prefix family inconsistency. |
| C-A2 | Medium | ORCH package path `app/orch/` vs existing tree tendencies toward `app/orchestration/` — implementation namespace collision risk. |
| C-D1 | High | **Dual fundamentals PIT:** E02 and E13 each imply separate PIT warehouses/ingests for overlapping fundamental concepts — hidden divergence risk. |
| C-D2 | Medium | `orch_*` control tables not clearly registered in E00 §13 taxonomy. |

## 2.6 Consistency summary

Cross-document consistency is **insufficient for a freeze baseline** until Blockers C-C1 and C-V1 are cleared. The architecture ideas align; the **configuration control** of those ideas does not.

---

# 3. Dependency Audit

## 3.1 Cycles

| ID | Sev | Finding |
|----|-----|---------|
| D-Y1 | Medium | Soft cycle risk: E14 consumes E01 and may feed stress confirmation narrative back toward CIO/E01 displays; acceptable if E14 **never rewrites** E01 regime labels (stated) — must be enforced in tests. |
| D-Y2 | Medium | E08 ↔ E09 bidirectional citation (vol scaling vs trend+vol conflicts) — OK as optional edges; must not become blocking mutual wait in ORCH DAG. |
| D-Y3 | Low | No hard L0←L7 dependency inversion found in normative layering text. |

## 3.2 Missing dependencies

| ID | Sev | Finding |
|----|-----|---------|
| D-M1 | **Blocker** | E00 E10 row: order **“After L4 views”** but Dependencies list **omits L4** (lists E01–E03, E13, specialised, E14). |
| D-M2 | High | E10 spec itself largely omits L4; schedules `e10_after_e03` earlier than L4 seal in places — **missing edge in the product that must consume composite opinions**. |
| D-M3 | High | E00 registry consumer lists for E05/E08/E11 under-mention L4 despite L4 exclusive voter set. |
| D-M4 | Medium | Shared L2 fundamentals ownership missing between E02/E13 (see C-D1). |

## 3.3 Unnecessary / hidden coupling

| ID | Sev | Finding |
|----|-----|---------|
| D-H1 | High | **E03 `A_TREND_PERS` / `SM_TREND_PERS`** overlaps conceptually with E09 CTA trend — L4 may double-count unless demean/exclude is mandatory, not optional. |
| D-H2 | High | E03 combiner still central while L4 also fuses E03 — migration dual-brain coupling for months/years. |
| D-H3 | Medium | Legacy `score_research` worker coupled into E03 dual-write — correct for migration, high operational coupling. |
| D-H4 | Medium | Options licensing couples E08 Production modules to procurement — architectural optional path exists, commercial dependency does not. |

## 3.4 Execution ordering conflicts

| ID | Sev | Finding |
|----|-----|---------|
| D-O1 | **Blocker** | **Three view-source truths:** (a) E00 canonical `L4 → E10`; (b) E10/E03 `E03 → E10`; (c) ORCH/IMP migration flag `e10_views_source` E03→L4. Not a single state machine. |
| D-O2 | High | E03 self-described order `E01→E02→E03→E14→E10` skips L4 entirely. |
| D-O3 | High | ORCH critical path treats E13 as off-critical parallel; E00 daily cycle lists E13 before specialised — acceptable if documented as performance shed, but “critical” semantics disagree. |
| D-O4 | Medium | L4 shadow allowed after E03 seal (ORCH) while also described as barrier before E10 — migration modes need one diagram. |

**Dependency verdict:** Layering philosophy is sound; **E10↔L4↔E03 ordering is the highest structural inconsistency short of redesign**.

---

# 4. Gap Analysis

## 4.1 Missing edge cases

| ID | Gap |
|----|-----|
| G1 | Corporate-action mid-day restatement invalidating sealed snapshot mid-distribute |
| G2 | Partial universe holiday calendars (NSE special sessions) vs IST cron map |
| G3 | Multi-listing / symbol remap (NSE renames) across Feature Registry + all engine currents |
| G4 | E04 pair leg halt / ban while basket still “active” |
| G5 | E05 event cancellation after score publish |
| G6 | Simultaneous E01 print revision + E14 stress (ordering of intraday refresh) |
| G7 | L4 voter clocks skew (E11 intraday vs E03 EOD) without as_of alignment rules beyond general PIT |
| G8 | Paper trading gap/open auction fill model under India market microstructure |

## 4.2 Missing operational procedures

| ID | Gap |
|----|-----|
| G9 | Sev-1 communications template to CIO (PRR requires runbooks; content not authored) |
| G10 | Vendor key rotation drill procedure |
| G11 | Snapshot corruption recovery step-by-step (ORCH states policy, no runbook text) |
| G12 | Merge/train procedure for Weight Registry seed review cadence |
| G13 | Holiday calendar ownership & freeze dates |

## 4.3 Missing testing

| ID | Gap |
|----|-----|
| G14 | Golden multi-engine fixture pack spanning E01+E03+E13+E14+L4 on one as_of |
| G15 | Contract fuzz tests for EngineState unknown fields / polarity inversion |
| G16 | Deterministic float tolerance policy per engine (mentioned, not standardized numerically) |
| G17 | Chaos suite automation beyond narrative (IMP schedules; no harness spec detail) |
| G18 | Dual-write parity battery size/pass thresholds for E03 cutover |

## 4.4 Missing observability

| ID | Gap |
|----|-----|
| G19 | Trace sampling policy under load |
| G20 | Data-quality scorecard SLIs (completeness by vendor) not first-class beside orch latency |
| G21 | Cost/latency budgets for NLP/E11 batch as SLO burn alerts |

## 4.5 Missing governance

| ID | Gap |
|----|-----|
| G22 | **Single configuration baseline:** all frozen markdown not merged to one release branch/`main` |
| G23 | Machine-readable document manifest (doc_id, version, git SHA, freeze hash) |
| G24 | E00 amendment RFC template (process mentioned, artifact thin) |
| G25 | Conflict resolution when PRR vs IMP dates disagree |

## 4.6 Missing documentation / APIs / validation

| ID | Gap |
|----|-----|
| G26 | Canonical OpenAPI for `/intelligence` + `/orch` jointly |
| G27 | Worked migration state machine doc (flags × UI × E10 views × L4 primary) — currently scattered |
| G28 | Pre-registered L4 superiority KPI sheet (PRR L4-S1 needs named KPI before shadow starts) |
| G29 | Data dictionary for Feature Registry v0 minimum viable feature list |
| G30 | Legal/compliance review checklist for public Beta disclaimers (research-only) |

---

# 5. Risk Assessment — Top 25 Implementation Risks

| Rank | ID | Risk | Prob. | Impact | Mitigation (no redesign) | Owner |
|-----:|----|------|-------|--------|--------------------------|-------|
| 1 | R01 | Specs remain on divergent PRs; engineers implement against stale E00 | H | H | Merge freeze corpus; publish manifest SHA; block impl PRs until baseline tag | Eng + Architecture |
| 2 | R02 | E10 built to E03-only while E00 assumes L4-first | H | H | Adopt ORCH `e10_views_source` state machine before E10 P0 coding; clarify E10 annex | Portfolio + Eng |
| 3 | R03 | EngineState field drift breaks L4 adapters | H | H | Land JSON Schema SSOT + CI against all engine fixtures before engine math P1 | Eng |
| 4 | R04 | E03 dual-write drift vs legacy `score_research` | M | H | Parity fixtures + IMP S09 gate; no UI cutover on fail | Quant Eng |
| 5 | R05 | L4 double-counts trend (E03 persistence + E09) | M | H | Mandatory exclude/demean rule in L4 voter prep tests | Quant |
| 6 | R06 | E14 false blocks stall Internal CIO adoption | M | H | Research vs promote path split tests; tune in Shadow only | Risk |
| 7 | R07 | PIT / look-ahead bug ships in features | M | H | Replay CI fail-closed; PRR A-R7 non-waivable | Eng + Quant |
| 8 | R08 | Weight Registry delayed; hardcodes sneak into Production | M | H | Lint ban + registry seed files in S17 before L4 shadow weights | Eng |
| 9 | R09 | Options/alt-data licenses block E08/E11 | H | M | Keep modules flagged off; L4 weight 0 path | Data + CIO |
| 10 | R10 | EOD over runtime; specialised shed silently drops voters | M | M | ETA monitor; explicit `best_effort` status in snapshot | Ops |
| 11 | R11 | Public Beta misread as advice/execution | M | H | PRR copy review; no order CTA; legal pass | CIO + Legal |
| 12 | R12 | Confidence scalar vs object causes silent 0/1 bugs | H | M | Adapter layer + contract tests (C-C2) | Eng |
| 13 | R13 | Dual fundamentals PIT (E02/E13) diverges | M | M | Shared L2 FUND_ builders; single ingest | Data + Quant |
| 14 | R14 | Shadow metrics gamed / short sample “superiority” | M | H | Pre-register KPI; 40-session + embargo; PRR L4-S* | Quant + Risk |
| 15 | R15 | On-call alert noise → ignored Sev-1 | M | M | SLO-based paging only; hypercare tuning | Ops |
| 16 | R16 | Redis/online cache serves wrong as_of | M | H | Cache key includes as_of; pit_mode disables latest | Eng |
| 17 | R17 | ORCH monolith bottleneck early | M | M | Keep orch thin; extract only per ORCH §14 later | Eng |
| 18 | R18 | Staffing <3 FTE slips critical path past 18 months | M | M | Protect S01–S09/S23 critical path; defer specialised UI | Eng Mgmt |
| 19 | R19 | Vendor 429s during EOD seal | H | M | Retry/quarantine; last-good policy matrix | Ops + Data |
| 20 | R20 | LLM polish enabled too early, invents claims | L | H | Flag default off; claim-bound tests | CIO Desk |
| 21 | R21 | DB migration expands without contract; breaks RLS | M | M | Expand/contract + RLS tests in CI | Eng |
| 22 | R22 | Paper P&L optimistic fills → false confidence | M | M | Conservative TCA defaults; watermark | Portfolio |
| 23 | R23 | Namespace clash `app/orch` vs `app/orchestration` | M | L | Choose one in S02; redirect shim | Eng |
| 24 | R24 | Holiday/calendar mistakes in cron | M | M | Calendar ownership + dry-run calendar | Ops |
| 25 | R25 | Premature “Architecture frozen” used to skip E00 sync amendments | H | H | Conditions in §11; refuse impl until C-V1/C-C1 closed | Architecture Board |

---

# 6. Architecture Debt

## 6.1 Duplicate concepts

| Debt | Why it hurts later |
|------|---------------------|
| E03 technical composite **and** L4 institutional opinion as “the score” | Years of UI/API ambiguity |
| E03 trend persistence **and** E09 CTA trend | Correlated voters, inflated confidence |
| E02 style quality/value **and** E13 fundamental quality/value | Two warehouses, two truths |
| ORCH “L5_” branding **and** E00 Layer 5 E10 | Training & ticket confusion |
| Per-engine schema.py **and** ORCH JSON Schema **and** E00 app/schemas | Triple SSOT failure mode |

## 6.2 Future maintenance risks

- 1,000+ line engine specs will drift from code without executable contracts  
- Flag matrix growth (IMP §11 × ORCH §13 × L4 §15) without a flag taxonomy test  
- Annex “v1.1 prefix” temporary aliases become permanent  
- Shadow tables retained forever without retention job  

## 6.3 Complexity hotspots

1. L4 fusion + hierarchy + calibration + Weight Registry conditions  
2. E03 dual-write + legacy worker + XS combiner  
3. E14 dual pass (firm prior + assess) across promote paths  
4. E10 constraint repair loop × E14 hard caps × view source switch  
5. ORCH barrier semantics under partial specialised failure  

## 6.4 Technical debt likely to emerge (even if well built)

| Likely debt | Trigger |
|-------------|---------|
| Adapter forest mapping scalar conf → conf-1.0 | If C-C2 not fixed first |
| “Just read E03 in E10” permanent flag | If L4 primary delayed |
| Copy-pasted PIT joins per engine | If L2 registry thin |
| Cron soup outside `orch_dag_*.json` | If jobs bypass ORCH |
| Dashboard special cases per engine | If widget contract absent |

---

# 7. Performance Assessment

## 7.1 Expected bottlenecks

| Bottleneck | Why |
|------------|-----|
| E03 full-universe EOD | Largest critical-path job; dual-write doubles work |
| L4 universe reduce | Barrier after many voters; explanation tree heavy |
| E08 chain ingest | Payload size / license / validation cost |
| E11 NLP batch | CPU/GPU & vendor rate limits |
| E10 optimiser under stress Σ blends | Repair iterations |

## 7.2 Scaling risks

- Vertical worker sizing on Render-class hosts before sharding  
- Snapshot/evidence graph storage growth  
- Interactive recompute stampedes after market open  

## 7.3 Database risks

- Hot `current` row contention if multiple writers  
- Missing composite indexes on `(as_of, symbol)` early  
- RLS misconfig denying service role mid-seal  
- PIT history without partitioning → vacuum death  

## 7.4 Caching risks

- Serving “latest” during `pit_mode` replay (called out; easy to miss in code)  
- CDN caching authenticated Beta content  
- Negative cache masking recovered vendor data too long  

## 7.5 Latency / memory risks

- Warm GET 300ms target fails if gateway fans out to cold engines synchronously  
- E02/E03/E13 8GB guidance exceeded when feature frames materialized eagerly  
- L4 explanation fetching full evidence blobs on list endpoints  

**Performance verdict:** Budgets are plausible for India research universes **if** interactive paths stay cache-first and EOD sheds specialised work — not yet proven.

---

# 8. Security Review

| Area | Assessment | Weakness |
|------|------------|----------|
| Authentication | Pattern exists (PIN/SSO mentions) | Role model for dual-control flag flips not fully specified as IAM matrix |
| Secrets | Correct law (env only) | Rotation drill gap (G10) |
| Supply chain | Under-specified | No pinned SBOM / dependency review gate in PRR beyond general CI |
| Dependency management | Implied via CI | No normative allowlist for native/data libs; ML stack future risk |
| Auditability | Strong on paper (flags, promotes, seals) | No retention/export legal hold procedure |
| Research/public boundary | Strong principle | Beta watermark enforcement needs automated tests |
| Prompt/LLM surface | Flagged off | Jailbreak/data exfil path if polish enabled without claim binder |

**Security verdict:** Adequate **design intent** for internal research; **insufficient evidenced controls** for institutional/licensed distribution.

---

# 9. Production Readiness Assessment

Evaluate architecture sufficiency (not implementation completion).

| Use case | Sufficient? | Rationale |
|----------|-------------|-----------|
| **Internal research** | **Conditionally yes** | Layers, engines, ORCH, PRR enough **after** consistency conditions; best near-term target |
| **Paper trading** | **Conditionally yes** | IMP/PRR define research-only paper loop; microstructure/TCA edge cases thin but acceptable for research |
| **Public website** | **Partially** | E03 incumbent path OK; institutional composite/L4/E10 public needs watermarks, legal, and gate packs |
| **Institutional clients** | **Not yet** | Needs soak, SLA evidence, warehouse, dual-control ops, contract SSOT, superiority packs — architecture points there, does not prove it |
| **Licensed investment products** | **No** | Explicitly out of research-only constitution; would need Execution/Product constitution + regulatory stack — **Requires E00 Amendment** (and likely new constitution), not IMP alone |

---

# 10. Recommendations

**IMPORTANT:** No Architecture v1.0 redesign. Items that change law are marked.

## 10.1 Minor clarifications (documentation)

1. Publish a **Migration State Machine** one-pager: flags × E03 UI × L4 shadow × `e10_views_source` × L4 primary (resolves D-O1 without redesign).  
2. Glossary: ban bare “L5” in tickets — say `E10` or `ORCH`.  
3. Label all numeric weight tables as **Weight Registry seeds**, not code constants (C-C5).  
4. Define “degraded E01” allowed fields vs “no invented regime” (C-level E01 wording).  
5. Pin L4 voter field per engine (`signal_id` / score path) in a single table.  
6. Mandate E03∩E09 overlap handling as **required demean/exclude**, not optional.  
7. Align conflict confidence cap example (0.55 vs 0.60) by doc errata — pick E00 as supreme number unless amended.

## 10.2 Documentation improvements

8. Machine-readable **freeze manifest** (`doc_id`, version, git SHA, freeze hash).  
9. Joint OpenAPI skeleton for intelligence + orch.  
10. Shared **L2 fundamentals** ownership note (E02 consumes; E13 consumes; one builder).  
11. Pre-registered **L4 superiority KPI sheet** before shadow day 1.  
12. E00 Annex B errata list including ORCH + L4 + IMP + PRR as governance corpus.

## 10.3 Testing improvements

13. Land EngineState JSON Schema + fixtures **before** engine math expansion.  
14. Golden multi-engine as_of pack (G14).  
15. Chaos tests automated for E11 down, E01 stale, E14 missing on promote.  
16. Dual-write parity thresholds codified.  
17. Float tolerance standard in `validation/tolerances.json`.

## 10.4 Implementation sequencing

18. **Do not start specialised engine UI** until S01–S09 + schema SSOT complete.  
19. Merge architecture PRs / tag `architecture-v1.0-freeze` before IMP S07 coding surge.  
20. E10 P0 must read `e10_views_source` (default `e03`) even if L4 immature.  
21. Weight Registry service before L4 shadow voter weights.  
22. Keep L4 primary off until PRR §5 pack — no calendar override.

## 10.5 Operational improvements

23. Author Sev-1 runbooks listed in PRR before Internal enable.  
24. Calendar owner + holiday file.  
25. Alert inventory with paging policy.  
26. Rollback drill on staging before first Beta flag.

## 10.6 Requires E00 Amendment

Mark these explicitly — **not to be sneaked into implementation PRs**:

| ID | Amendment needed |
|----|------------------|
| E00-A1 | Update engine registry rows: E04/E05/E08/E09/E11 normative specs exist; adjust §20.1 v1.1 language |
| E00-A2 | Annex B include ORCH, L4, IMP-V1, PRR-V1 as governance corpus |
| E00-A3 | §6 add `TREND_` / `RVAL_` / `ALT_` (or formally defer and force temporary aliases only) |
| E00-A4 | §5.3 explicit shim map: scalar confidence → conf-1.0; domain score → `score{}` |
| E00-A5 | E10 dependencies must list L4; bind migration end-state for views |
| E00-A6 | §11 ladder vs L4 extended hierarchy reconciliation (which is normative detail) |
| E00-A7 | §14 API prefix reconciliation with ORCH `/api/v1/orch` |
| E00-A8 | §13 register `orch_*` platform tables |
| E00-A9 | Canonical schema path single choice (`app/schemas` vs `contracts/vN`) |
| E00-A10 | Any licensed-product / execution pathway (new constitution) |

---

# 11. Final Verdict

## **APPROVED WITH CONDITIONS**

### Why not APPROVED

Blockers remain in **configuration control and cross-doc truth**:

1. E00 still says specialised specs pending / v1.1 while freeze claims them frozen (**C-V1**).  
2. No EngineState schema SSOT on an integrated baseline (**C-C1**).  
3. E10 ↔ L4 ↔ E03 view-source / ordering triple conflict (**D-O1 / D-M1 / D-M2**).  
4. conf-1.0 / evidence example drift across frozen engines (**C-C2 / C-C3**).  
5. Institutional / licensed-product bars not met (expected at this stage, but forbids unconditional approval).

### Why not MAJOR REWORK REQUIRED / REJECTED

- Layering L0–L8, research-only boundary, E14 fail-closed, Weight Registry law, shadow-before-crown L4, ORCH control plane, IMP sequencing, and PRR gates are **coherent institutional architecture**.  
- Issues are predominantly **consistency, SSOT, migration state machine, and baseline control** — not a failed philosophy.  
- Remediation is mostly **errata + E00 amendments + test harness sequencing**, not a redesign of engines.

### Conditions precedent (must close before IMP Phase 1 engine coding surge)

| # | Condition | Exit evidence |
|---|-----------|---------------|
| 1 | Single freeze baseline on mergeable branch/`main` + manifest SHA | Tag `architecture-v1.0-freeze` |
| 2 | E00 amendments E00-A1, E00-A2, E00-A5, E00-A9 filed or explicitly scheduled as first amendment sprint | Amendment PRs or board waiver recording deferral dates |
| 3 | EngineState JSON Schema SSOT + fixtures for E01/E03/E14/L4 minimum | CI green |
| 4 | Published Migration State Machine (E03/L4/E10 flags) | Doc linked from ORCH/IMP |
| 5 | Pre-registered L4 superiority KPI sheet | Quant signed |
| 6 | PRR lite process adopted on next merge | Template used |

### Board statement

> Architecture v1.0 is **good enough to build toward Internal Research and Shadow**, provided conditions above are treated as **flight constraints**.  
> It is **not** approved for public institutional composite primacy, nor for licensed investment products, without further E00-governed work and evidenced PRR Production packs.

---

# Annex A — Evidence index (audit anchors)

| Theme | Primary anchors |
|-------|-----------------|
| E00 pending vs freeze | E00 registry “spec pending”; E00 §20.1 v1.1; engine headers Candidate-track; ORCH freeze list |
| L5 naming | ORCH naming clarification table; E00 §2.6 Layer 5 = E10 |
| E10 vs L4 | E00 E10 order/dependencies; E10 cron/views; ORCH `e10_views_source`; L4 §15 flags |
| conf-1.0 | E00 §5/§9; engine examples; L4 input registry |
| Prefix debt | E00 §6; E04/E09/E11 annex notes |
| Repo reality | `origin/main` lacks intelligence-engine architecture markdown corpus at audit time |

---

# Annex B — Score rationale (compact)

| Score | Drivers up | Drivers down |
|-------|------------|--------------|
| Architecture 74 | Layering, E14, Weight Registry, L4 shadow law | Consistency blockers, naming hazard |
| Engineering 38 | IMP/PRR actionable | No integrated code/schema baseline |
| Scalability 62 | ORCH parallel/shed | EOD monolith risk, storage |
| Maintainability 58 | Clear owners on paper | Doc sprawl, dual PIT, dual scores |
| Research quality 79 | PIT/evidence/shadow philosophy | Double-count & contract drift |
| Ops readiness 45 | Metrics/runbook lists | No evidenced drills |
| Institutional 41 | Path exists | Clients/licensed not ready |

---

# Annex C — Document control

| Version | Notes |
|---------|-------|
| 1.0.0 | Initial independent Architecture v1.0 review; verdict APPROVED WITH CONDITIONS |

This report does **not** amend Architecture v1.0. Clearing conditions may require **E00 Amendment** items listed in §10.6; until then, implementation must not assume contradictory docs are all simultaneously true.

---

*End of ARCHITECTURE V1 REVIEW REPORT — independent pre-implementation audit*
