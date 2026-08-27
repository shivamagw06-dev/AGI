# ARCHITECTURE v1.0.1 STABILISATION PROGRAMME  
## Consistency Hardening Before Large-Scale Implementation

**Document ID:** `STAB-1.0.1`  
**Filename:** `ARCHITECTURE_V1_0_1_STABILISATION_PROGRAMME.md`  
**Parent baseline:** Architecture v1.0 Feature Freeze  
**Trigger:** `AVR-V1` verdict — **APPROVED WITH CONDITIONS** (composite **57/100**)  
**Target:** Architecture **v1.0.1** — composite review score **≥ 80/100**  
**Status:** Binding short-lived programme (then retire)  
**Version:** 1.0.0  
**Owner:** Head of Research Engineering / Architecture Board / CIO  
**Nature:** **Stabilisation only** — no redesign, no new engines, no philosophy change

### Programme law

1. **Architecture redesign is prohibited.**  
2. Investment philosophy, engine responsibilities, L0–L8 layering, and E14 authority **do not change**.  
3. Only **consistency, governance text, contracts, naming, tests, and implementation readiness** may change.  
4. Changes that alter law use the minimal **E00 Amendment (patch)** path — still not a redesign.  
5. Large-scale IMP-V1 Phase 1 engine coding surge **waits** until v1.0.1 Release Checklist Pass.  
6. Success metric: clear AVR-V1 blockers C-V1, C-C1, D-O1/D-M1, C-C2/C-C3, C-N1 and raise score **57 → ≥80**.

### In scope

| Blocker | AVR-V1 IDs |
|---------|------------|
| E00 “pending/future” vs freeze | C-V1, C-V2, C-V4, E00-A1/A2 |
| Canonical EngineState SSOT | C-C1, C-C4, E00-A9 |
| Portfolio flow E00/L4/E03/ORCH | D-O1, D-M1, D-M2, E00-A5 |
| conf-1.0 + Evidence drift | C-C2, C-C3, C-S1, E00-A4 |
| ORCH `L5_` vs E00 Layer 5 | C-N1, C-N3 |

### Out of scope

- New engines (E06/E07/E12 specs, new IDs)  
- Changing L4 fusion math philosophy  
- Changing E03 primary-until-superiority rule  
- Execution / licensed-product constitutions  
- Full IMP-V1 specialised UI builds  

---

# 1. Target Outcome — Architecture v1.0.1

| Attribute | v1.0 (today) | v1.0.1 (exit) |
|-----------|--------------|---------------|
| Freeze claim vs E00 registry | Contradictory | Aligned |
| EngineState schema | Fragmented / absent on main | Single SSOT + CI |
| Portfolio views path | Triple narrative | One state machine + doc sync |
| conf-1.0 / evidence | Drifted examples | Normative shims + fixtures |
| ORCH naming | `L5_` ambiguity | Harmonised aliases + glossary ban on bare “L5” |
| Review score | 57 | **≥ 80** |
| IMP Phase 1 surge | Blocked by conditions | Unblocked |

**Version semantics:** `1.0.1` = **patch stabilisation** of Architecture v1.0 (errata + contract SSOT + amendments), not Architecture v1.1 feature expansion.

---

# 2. Blocker Remediation Specs

---

## Blocker B1 — E00 “pending / future” vs frozen engine specs

### Problem
E00 registry and §20.1 still describe E04/E05/E08/E09/E11 (and related) as **spec pending** or deferred to **v1.1**, while Architecture v1.0 freeze / ORCH / IMP / AVR treat those specs as **complete and frozen**.

### Impact
Engineers and reviewers cannot know which document is authoritative; lifecycle status may be illegally skipped; freeze credibility collapses.

### Root cause
E00 was authored before specialised engine PRs landed; freeze declaration advanced without an E00 patch amendment.

### Required documents
| Doc | Change type |
|-----|-------------|
| `E00_AGI_INVESTMENT_OFFICE_CONSTITUTION.md` | **E00 Amendment (patch)** — registry rows, Annex B, §20.1 |
| `ARCHITECTURE_V1_REVIEW_REPORT.md` | Note conditions clearance (optional follow-up) |
| Freeze manifest `architecture-v1.0.1-manifest.json` | New |

### Required PRs
1. `cursor/e00-v1-0-1-registry-sync-4cc0` — E00 patch only  
2. `cursor/arch-manifest-v1-0-1-4cc0` — machine-readable manifest of all frozen doc SHAs  

### Required tests
| Test | Asserts |
|------|---------|
| `test_e00_registry_matches_manifest` | Every freeze-listed engine has E00 status ≠ “spec pending” |
| `test_annex_b_includes_governance_corpus` | Annex B lists E00, ORCH, L4, IMP-V1, PRR-V1, engine specs |
| `test_no_v11_for_frozen_specs` | §20.1 does not list already-frozen specs as future work |

### Acceptance criteria
- [ ] E00 E04/E05/E08/E09/E11 rows say **spec frozen** (lifecycle may remain Experimental/Research/Candidate as appropriate)  
- [ ] §20.1 v1.1 language no longer claims “complete specs for E04–E09, E11” as future  
- [ ] Annex B includes ORCH, L4, IMP-V1, PRR-V1  
- [ ] Manifest lists doc_id, path, version, git SHA  

### Migration plan
1. Draft E00 patch diff (text only).  
2. Board ACK (Architecture + Eng).  
3. Merge after schema PR path agreed (can parallel B2).  
4. Tag `architecture-v1.0.1-rc1` when B1–B5 green.

### Rollback
Revert E00 patch PR; restore prior Annex/registry; keep engine specs untouched.

### Estimated effort
**5 eng-days** (doc + tests)

### Owner
Architecture Board / Head of Research Engineering

---

## Blocker B2 — No canonical EngineState schema SSOT

### Problem
E00 cites `app/schemas/` + per-engine `schema.py`; ORCH cites `contracts/v{N}/...` and `app/orch/contracts/engine_state.schema.json`. No single schema exists as CI-enforced SSOT on the integration baseline.

### Impact
L4/ORCH adapters will break; promotion gates cannot be machine-checked; AVR engineering score stays low.

### Root cause
Contract law was specified narratively before a single artifact was chosen and landed.

### Required documents
| Doc | Change type |
|-----|-------------|
| E00 §5 / §19 | **E00 Amendment (patch)** — declare canonical path |
| ORCH §8 / §17 | Errata — point to same path |
| Engine specs | Errata note: “examples subordinate to SSOT schema” |
| `contracts/v1/engine_state.schema.json` | **New normative artifact** |
| `contracts/v1/shims.md` | Scalar/domain → envelope mapping |

### Required PRs
1. `cursor/engine-state-schema-ssot-4cc0` — schema + fixtures + CI  
2. `cursor/e00-v1-0-1-schema-path-4cc0` — E00 canonical path (may combine with B1)  
3. `cursor/orch-l4-schema-errata-4cc0` — ORCH/L4 path alignment  

**Canonical choice for v1.0.1 (stabilisation, not redesign):**

```
intelligence-engine/contracts/v1/engine_state.schema.json   # SSOT
intelligence-engine/contracts/v1/fixtures/**               # golden JSON
intelligence-engine/app/schemas/engine_state.py            # generated/typed mirror (optional)
```

Per-engine `schema.py` may **extend** via `$defs` / `allOf`, never fork the envelope.

### Required tests
| Test | Asserts |
|------|---------|
| `test_engine_state_schema_loads` | Schema valid JSON Schema draft |
| `test_fixture_<engine>_validates` | E01/E02/E03/E04/E05/E08/E09/E10/E11/E13/E14/L4 fixtures validate |
| `test_no_duplicate_ssot_paths` | CI fails if second “canonical” schema path drifts without pointer file |
| `test_score_and_confidence_object_shape` | `score` + `confidence.method_version == conf-1.0` present on Candidate+ fixtures |

### Acceptance criteria
- [ ] One path declared in E00 as SSOT  
- [ ] ORCH/L4 reference identical path  
- [ ] Minimum fixtures: E01, E03, E14, L4, E10 (+ others or explicit waiver list)  
- [ ] CI job `contracts` required on PRs touching engines/orch/l4  

### Migration plan
1. Land empty-envelope schema + E01/E03/E14 fixtures first.  
2. Add remaining engine fixtures (shim-allowed).  
3. E00/ORCH errata merge.  
4. Ban new engine examples that violate schema (doc test).

### Rollback
Feature-flag CI to warn-only; keep schema file; do not delete fixtures.

### Estimated effort
**10 eng-days**

### Owner
Head of Research Engineering / Quant Eng

---

## Blocker B3 — Portfolio flow conflict (E00 L4→E10 vs E03→E10 vs ORCH flag)

### Problem
Three simultaneous truths: E00 canonical `L4 → E10`; E03/E10 operational `E03 → E10`; ORCH `e10_views_source` migration flag.

### Impact
E10 implementers will build the wrong default; L4 promotion path undefined; AVR dependency blockers remain.

### Root cause
Migration reality (E03 incumbent) was not encoded as a single normative state machine inside E00/E10 while E00 already stated L4-before-E10 as steady state.

### Required documents
| Doc | Change type |
|-----|-------------|
| `PORTFOLIO_VIEWS_MIGRATION_STATE_MACHINE.md` | **New clarification doc** (not new architecture) |
| E00 E10 registry row | **E00 Amendment (patch)** — Dependencies include L4; migration end-state |
| E10 spec | Errata — honor `e10_views_source`; default `e03` until L4 primary |
| ORCH §1 / §13 | Errata — link state machine; cron order notes |
| L4 §15 | Errata — cross-link flags |

### Required PRs
1. `cursor/portfolio-views-state-machine-4cc0` — state machine doc + diagram  
2. `cursor/e00-e10-l4-dependency-patch-4cc0` — E00 deps + end-state  
3. `cursor/e10-orch-l4-views-errata-4cc0` — E10/ORCH/L4 sync  

### Normative stabilisation rule (no redesign)

| Mode | `e10_views_source` | E10 reads | UI primary research score | Allowed when |
|------|--------------------|-----------|---------------------------|--------------|
| M0 Incumbent | `e03` | E03 (+ E01/E14…) | E03 | Default v1.0.1 |
| M1 Dual | `e03` + L4 shadow ignored by E10 | E03 | E03; L4 shadow internal | L4 shadow on |
| M2 Shadow views | `l4_shadow` | L4 shadow opinions (non-prod sizing) | E03 | Internal/paper only |
| M3 Primary | `l4` | L4 Production opinions | L4 (E03 voter remains) | PRR §5 Pass only |

E00 steady-state remains **L4 → E10** at **M3**. v1.0.1 makes **M0 default** explicit so docs stop contradicting.

### Required tests
| Test | Asserts |
|------|---------|
| `test_e10_default_views_source_e03` | Default flag `e03` |
| `test_e10_rejects_l4_primary_without_prr_pack` | Cannot set `l4` without gate artifact stub |
| `test_state_machine_doc_matches_flags` | Doc enumerates exact flag keys in ORCH/L4/IMP |
| `test_e00_e10_dependencies_include_l4` | Doc test / manifest |

### Acceptance criteria
- [ ] Single state machine doc linked from E00, E10, ORCH, L4, IMP  
- [ ] E00 E10 Dependencies **include L4**  
- [ ] E10 errata states default `e03` and M3 end-state  
- [ ] No remaining prose that E10 “always” reads only E03 **or** only L4 without mode  

### Migration plan
Document-only for v1.0.1; runtime flag wired in IMP S27 but **contracted now**.

### Rollback
Revert errata; state machine doc marked superseded — avoid during IMP E10 coding.

### Estimated effort
**6 eng-days**

### Owner
Portfolio Construction Lead / Architecture Board

---

## Blocker B4 — conf-1.0 and Evidence object drift

### Problem
E00 mandates `confidence: {value, components, method_version:"conf-1.0"}` and §10 evidence buckets; frozen engine examples use scalars/aliases and often omit evidence packs.

### Impact
L4 fusion and PRR promote packs cannot rely on fields; silent 0/1 bugs; research quality score capped.

### Root cause
Engine specs predated strict envelope examples; no shim registry or fixture CI.

### Required documents
| Doc | Change type |
|-----|-------------|
| E00 §5.3 | **E00 Amendment (patch)** — normative shim map |
| `contracts/v1/shims.md` | Confidence + evidence + score mappings |
| `contracts/v1/evidence.schema.json` | Evidence pack schema (component of envelope) |
| Engine specs | Errata: examples updated **or** marked non-normative vs fixtures |
| L4 input registry | Errata: read path via shim layer |

### Required PRs
1. `cursor/conf-evidence-shim-registry-4cc0` — shims + schemas + fixtures  
2. `cursor/engine-spec-envelope-errata-4cc0` — patch examples / “subordinate to fixtures” banners  
3. (shares CI with B2)

### Shim rules (stabilisation)

| Legacy field | Canonical |
|--------------|-----------|
| `confidence: number` | `confidence.value`; `components: {legacy_scalar: n}`; `method_version: conf-1.0` |
| `factor_confidence` / `fundamental_confidence` / `trend_confidence` | Map into `confidence.value` + component key; keep alias in `metadata.aliases` |
| Missing evidence | Empty arrays required keys; `missing_data` explains absence — **never omit object** |
| Domain score only | Fill `score.normalized_0_100` or `normalized_signed` via declared polarity map |

### Required tests
| Test | Asserts |
|------|---------|
| `test_all_fixtures_conf_method_version` | `== "conf-1.0"` |
| `test_evidence_keys_present` | positive/negative/contradictions/unknowns/risks/missing_data |
| `test_shim_scalar_confidence` | Adapter golden tests |
| `test_l4_adapter_reads_shims` | L4 client accepts shimmed E03/E01 samples |
| `test_docs_examples_or_banner` | Doc test: example JSON validates **or** file contains subordinate-banner |

### Acceptance criteria
- [ ] Shim registry merged  
- [ ] E01/E03/E14/L4 fixtures full envelope  
- [ ] ≥80% of frozen engine fixtures validate without warn; remainder on tracked waiver expiring at IMP S22  
- [ ] E00 §5.3 cites shim file  

### Migration plan
Fixtures first → adapters → doc example cleanup. Code generators may emit shims until examples updated.

### Rollback
Waivers in `contracts/v1/waivers.yaml`; CI warn-only for non-critical engines.

### Estimated effort
**8 eng-days**

### Owner
Quant Eng / Head of Quant Research

---

## Blocker B5 — ORCH `L5_` filename vs E00 Layer 5 (E10)

### Problem
Control-plane file `L5_ENGINE_INTERACTION_ORCHESTRATION.md` collides cognitively with E00 Layer 5 = Portfolio Construction (E10).

### Impact
Tickets, APIs, and onboarding mis-route work to the wrong layer; maintainability score suffers.

### Root cause
CIO series filename used `L5_` after L4 doc; E00 Layer 5 already meant E10.

### Required documents
| Doc | Change type |
|-----|-------------|
| ORCH | Naming section strengthened; canonical cite `Document ID: ORCH` |
| E00 §2 / §7 | Errata: consumer targets `E10` or `ORCH`, never bare `L5` |
| Glossary in freeze manifest | Ban list |
| Optional rename pointer | `ORCH_ENGINE_INTERACTION.md` stub → same content **or** keep filename + alias file |

### Required PRs
1. `cursor/orch-naming-harmonisation-4cc0` — alias file + glossary + E00/ORCH errata  

**v1.0.1 rule (minimal churn):**  
- Keep git history file `L5_ENGINE_INTERACTION_ORCHESTRATION.md` **or** add thin alias `ORCH_ENGINE_INTERACTION_ORCHESTRATION.md` that states canonical Document ID `ORCH`.  
- **Human/docs/API prose ban:** bare token `L5` meaning ORCH.  
- Layer references: `E00 Layer 5 (E10 Portfolio Construction)` vs `ORCH control plane`.

### Required tests
| Test | Asserts |
|------|---------|
| `test_glossary_bans_bare_l5` | Manifest/glossary contains ban |
| `test_e00_no_l5_consumer_token` | E00 consumer columns use E10/ORCH |
| `test_orch_alias_resolves` | Alias path exists and declares Document ID ORCH |

### Acceptance criteria
- [ ] Alias or rename pointer live  
- [ ] E00 errata removes ambiguous `L5` consumer meaning  
- [ ] IMP/PRR/AVR cross-links say ORCH not “L5 orchestration layer”  

### Migration plan
Docs-only; no runtime rename of packages required in v1.0.1 (package `app/orch` already distinct).

### Rollback
Remove alias file; keep clarification paragraph in ORCH header.

### Estimated effort
**3 eng-days**

### Owner
Head of Research Engineering / Architecture Board

---

# 3. Implementation Sequence (Stabilisation Sprints)

Short sprints (**1 week** each). May parallelise where noted. Total critical path **~7 weeks** calendar with 2 engineers; effort sum ~32 eng-days (+ buffer).

---

## Sprint S-1 — Freeze terminology & manifest

| Field | Content |
|-------|---------|
| **Objective** | One vocabulary + machine-readable freeze list |
| **Deliverables** | `architecture-v1.0.1-manifest.json`; glossary (ORCH vs E00 Layer 5; M0–M3 modes); ban bare `L5`; link AVR conditions |
| **Dependencies** | AVR-V1 |
| **Blockers addressed** | B5 (start), B1 (prep) |
| **Acceptance** | Manifest lists all governance + engine docs; glossary merged |
| **Effort** | 3 eng-days |
| **Owner** | Architecture Board |

---

## Sprint S-2 — Canonical EngineState SSOT

| Field | Content |
|-------|---------|
| **Objective** | Land `contracts/v1/engine_state.schema.json` + CI |
| **Deliverables** | Schema; pointer in repo; fixtures E01/E03/E14/L4; CI job `contracts` |
| **Dependencies** | S-1 |
| **Blockers addressed** | B2 |
| **Acceptance** | B2 acceptance criteria Pass |
| **Effort** | 6 eng-days |
| **Owner** | Research Engineering |

---

## Sprint S-3 — Evidence Registry (schema + fixtures)

| Field | Content |
|-------|---------|
| **Objective** | Evidence pack schema + required keys enforced |
| **Deliverables** | `evidence` `$defs` in SSOT; fixtures with full buckets; doc banners on non-compliant examples |
| **Dependencies** | S-2 |
| **Blockers addressed** | B4 (evidence half) |
| **Acceptance** | `test_evidence_keys_present` green on priority engines |
| **Effort** | 4 eng-days |
| **Owner** | Quant Eng |

---

## Sprint S-4 — Confidence Registry (conf-1.0 shims)

| Field | Content |
|-------|---------|
| **Objective** | Normative shim map + adapter tests |
| **Deliverables** | `contracts/v1/shims.md`; E00 §5.3 patch; scalar→object goldens; L4 read adapter tests |
| **Dependencies** | S-2, S-3 |
| **Blockers addressed** | B4 (confidence half), C-S1 cap errata if touched |
| **Acceptance** | All priority fixtures `method_version=conf-1.0` |
| **Effort** | 5 eng-days |
| **Owner** | Quant Eng / Architecture |

---

## Sprint S-5 — Portfolio dependency alignment

| Field | Content |
|-------|---------|
| **Objective** | Single M0–M3 state machine; E00/E10/ORCH/L4 agree |
| **Deliverables** | `PORTFOLIO_VIEWS_MIGRATION_STATE_MACHINE.md`; E00 E10 deps+end-state; E10/ORCH/L4 errata; flag default tests |
| **Dependencies** | S-1 |
| **Blockers addressed** | B3 |
| **Acceptance** | B3 acceptance criteria Pass |
| **Effort** | 5 eng-days |
| **Owner** | Portfolio Lead / Architecture |

*Note: S-5 may run partly parallel to S-2/S-3.*

---

## Sprint S-6 — Naming harmonisation + E00 registry sync

| Field | Content |
|-------|---------|
| **Objective** | Close B1 + finish B5; Annex B + §20.1 patch |
| **Deliverables** | E00 registry “spec frozen” rows; Annex B governance corpus; ORCH alias file; consumer token cleanup; prefix note (TREND_/RVAL_/ALT_ deferred explicitly **or** minimal §6 add — prefer **explicit deferral statement** in v1.0.1 to avoid scope creep; dual-alias remains documented) |
| **Dependencies** | S-1; preferably after S-5 |
| **Blockers addressed** | B1, B5 |
| **Acceptance** | B1 + B5 acceptance criteria Pass; doc tests green |
| **Effort** | 5 eng-days |
| **Owner** | Architecture Board |

---

## Sprint S-7 — Architecture re-audit (v1.0.1 gate)

| Field | Content |
|-------|---------|
| **Objective** | Independent delta audit vs AVR-V1; score ≥80; release checklist |
| **Deliverables** | `ARCHITECTURE_V1_0_1_REAUDIT_NOTE.md` (short); signed Release Checklist; tag `architecture-v1.0.1` |
| **Dependencies** | S-1…S-6 all Pass |
| **Blockers addressed** | Verification of B1–B5 closure |
| **Acceptance** | Re-audit score ≥80; zero open Blockers from AVR list in scope; IMP Phase 1 unblocked |
| **Effort** | 4 eng-days |
| **Owner** | Architecture Review Board |

---

### Sequence diagram

```
S-1 Terminology/Manifest
        ├─→ S-2 EngineState SSOT → S-3 Evidence → S-4 Confidence shims
        └─→ S-5 Portfolio state machine
                ↓
        S-6 E00 registry + naming
                ↓
        S-7 Re-audit → tag v1.0.1 → IMP Phase 1 surge allowed
```

---

# 4. Checklists

## 4.1 Stabilisation PR checklist (every STAB PR)

- [ ] No new engine IDs / no layer redesign  
- [ ] Cites AVR-V1 blocker IDs (B1–B5)  
- [ ] Cites E00 section if amending law  
- [ ] Updates manifest if normative doc changes  
- [ ] Adds/adjusts tests listed for that blocker  
- [ ] Rollback notes in PR body  
- [ ] Does not flip Production/L4-primary flags  

## 4.2 Documentation checklist

- [ ] E00 registry synced (B1)  
- [ ] Annex B complete (B1)  
- [ ] Schema path identical in E00/ORCH/L4 (B2)  
- [ ] State machine linked from E00/E10/ORCH/L4/IMP (B3)  
- [ ] Shim registry linked from E00 §5.3 (B4)  
- [ ] ORCH alias + glossary ban bare `L5` (B5)  
- [ ] All examples validate **or** carry subordinate banner  

## 4.3 Engineering readiness checklist (exit)

- [ ] `contracts` CI required  
- [ ] Fixtures for E01/E03/E14/L4/E10  
- [ ] Flag defaults: `e10_views_source=e03`, L4 primary false  
- [ ] Manifest SHA published  
- [ ] IMP-V1 notes “blocked until v1.0.1” removed or updated  

---

# 5. Test Programme

## 5.1 Regression tests

| ID | Test | Purpose |
|----|------|---------|
| RT1 | E03 Production primary flags unchanged by stabilisation merges | Incumbent protection |
| RT2 | ORCH document ID remains `ORCH` after alias | Naming |
| RT3 | L4 voter set unchanged (no new engines) | Scope lock |
| RT4 | E14 fail-closed promote rule text still present in E00/ORCH/PRR | Safety |

## 5.2 Contract tests

| ID | Test | Purpose |
|----|------|---------|
| CT1 | Envelope required fields present | SSOT |
| CT2 | Unknown required-field removal fails CI | Anti-drift |
| CT3 | Polarity declaration present when signed scores used | E00 §8 |
| CT4 | Weight tables labeled as registry seeds in docs (doc contract) | E00 §12 |

## 5.3 Schema tests

| ID | Test | Purpose |
|----|------|---------|
| ST1 | JSON Schema validates fixtures | B2 |
| ST2 | conf-1.0 method_version | B4 |
| ST3 | Evidence keys | B4 |
| ST4 | L4Opinion fixture validates | B2/B4 |
| ST5 | E10 portfolio fixture validates | B2/B3 |

## 5.4 Documentation tests

| ID | Test | Purpose |
|----|------|---------|
| DT1 | Manifest paths exist in repo | B1 |
| DT2 | E00 has no “spec pending” for freeze-listed engines | B1 |
| DT3 | State machine contains M0–M3 and flag keys | B3 |
| DT4 | No bare `L5` as consumer token in E00 | B5 |
| DT5 | ORCH alias file declares Document ID ORCH | B5 |
| DT6 | Scorecard target note references ≥80 exit | Programme |

---

# 6. Score Uplift Model (57 → ≥80)

| Dimension | v1.0 | v1.0.1 target | Mechanism |
|-----------|-----:|-------------:|-----------|
| Architecture | 74 | **86** | B1/B3/B5 consistency |
| Engineering | 38 | **72** | Schema SSOT + CI |
| Scalability | 62 | **68** | Unchanged philosophy; clearer EOD shed docs only |
| Maintainability | 58 | **78** | Naming + single contracts path |
| Research quality | 79 | **85** | conf/evidence fixtures |
| Ops readiness | 45 | **60** | Manifest + doc tests (runbooks still IMP) |
| Institutional | 41 | **55** | Governance corpus complete; still not licensed-product ready |
| **Composite** | **57** | **≥80** | Re-audit S-7 |

If S-7 scores **<80**, open only residual clarifications — **do not redesign**; extend waivers with dates, re-run S-7.

---

# 7. Architecture v1.0.1 Release Checklist

All items **Pass** required to tag `architecture-v1.0.1` and unblock IMP-V1 Phase 1 surge.

## 7.1 Blocker closure

- [ ] **B1** E00 registry/Annex/§20.1 synced; manifest live  
- [ ] **B2** EngineState SSOT path live; CI green; priority fixtures valid  
- [ ] **B3** Portfolio views state machine live; E00 E10 deps include L4; default M0=`e03`  
- [ ] **B4** conf-1.0 + evidence shims + fixtures; E00 §5.3 cites shims  
- [ ] **B5** ORCH alias + glossary ban bare `L5`; E00 consumer tokens cleaned  

## 7.2 Governance

- [ ] E00 patch amendments merged (A1/A2/A4/A5/A9 minimum)  
- [ ] ORCH/L4/E10/IMP errata merged  
- [ ] PRR still supreme for promotion (unchanged philosophy)  
- [ ] No new engines introduced  
- [ ] AVR conditions precedent #1–#6 addressed or explicitly dated  

## 7.3 Tests

- [ ] Regression RT1–RT4 Pass  
- [ ] Contract CT1–CT4 Pass  
- [ ] Schema ST1–ST5 Pass  
- [ ] Documentation DT1–DT6 Pass  

## 7.4 Re-audit

- [ ] S-7 re-audit note published  
- [ ] Composite score **≥ 80**  
- [ ] Zero open **Blocker** severity items from AVR scope B1–B5  
- [ ] Residual Medium/Low items tracked in IMP backlog (not freeze-breaking)  

## 7.5 Release actions

- [ ] Tag `architecture-v1.0.1`  
- [ ] Publish manifest SHA in release notes  
- [ ] Update IMP-V1 header: “Blocked on v1.0.1” → “v1.0.1 satisfied; Phase 1 authorised”  
- [ ] Architecture Board + Engineering + Quant sign-off  
- [ ] Announce: large-scale implementation may proceed under IMP-V1 + PRR-V1  

## 7.6 Explicit non-claims after v1.0.1

- [ ] Not a claim of Production engine implementation completion  
- [ ] Not L4 primary approval  
- [ ] Not institutional client / licensed-product readiness  
- [ ] Not Architecture v1.1 (no new engine specs required for this tag)

---

# 8. RACI (stabilisation)

| Work | Architecture | Eng | Quant | Portfolio | Risk | CIO |
|------|--------------|-----|-------|-----------|------|-----|
| B1 E00 sync | A | R | C | I | C | I |
| B2 Schema SSOT | C | A/R | R | I | I | I |
| B3 Portfolio SM | A | R | C | A/R | C | C |
| B4 conf/evidence | C | R | A/R | I | C | I |
| B5 naming | A/R | R | I | I | I | C |
| S-7 re-audit | A | R | R | C | C | C |

R=Responsible, A=Accountable, C=Consulted, I=Informed

---

# 9. Relationship to IMP-V1 / PRR-V1

| Programme | Role during stabilisation |
|-----------|---------------------------|
| **STAB-1.0.1** | Clears AVR conditions; owns S-1…S-7 |
| **IMP-V1** | Paused for Phase 1 *surge*; S01–S03 may prepare repo layout **without** violating SSOT once S-2 lands |
| **PRR-V1** | Unchanged; still gates Production |

**Hard gate:** No IMP sprint that implements new engine research math beyond contract fixtures until §7 Release Checklist Pass.

---

# 10. Document control

| Version | Notes |
|---------|-------|
| 1.0.0 | Initial stabilisation programme to reach Architecture v1.0.1 |

**Retirement:** After tag `architecture-v1.0.1` and IMP unblock, this programme becomes historical; further work follows IMP-V1 + PRR-V1 under E00.

---

*End of ARCHITECTURE v1.0.1 STABILISATION PROGRAMME — consistency hardening without redesign*
