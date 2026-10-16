# PRODUCTION READINESS REVIEW V1  
## Final Governance Gate — AGI Investment Office

**Document ID:** `PRR-V1`  
**Filename:** `PRODUCTION_READINESS_REVIEW_V1.md`  
**Architecture basis:** **E00 Architecture v1.0 — COMPLETE / FEATURE FROZEN**  
**Programme basis:** `IMPLEMENTATION_MASTER_PROGRAMME_V1.md` (`IMP-V1`)  
**Status:** Binding production-governance standard  
**Version:** 1.0.0  
**Owner:** CIO / Head of Research Engineering / Head of Risk / Head of Quantitative Research  
**Audience:** Engineering, Quant Research, Risk, Data, Operations, Architecture reviewers  
**Nature:** **Governance only** — not an architecture specification

### Constitutional position

| Document | Role after Architecture Complete |
|----------|----------------------------------|
| E00, ORCH, L4, E0X engine specs, IMP-V1 | **Frozen** — amend only via E00 governance |
| **This document (PRR-V1)** | **Final gate** deciding whether work may promote toward Production |
| Subsequent PRs | **Implementation, testing, validation, backtesting, operations** — not new architecture |

**Supremacy:** Subordinate to E00. On conflict with engine/ORCH/L4 specs, **E00 wins**; PRR enforces those specs — it does not rewrite them.

### Scope of a PRR

A Production Readiness Review is required for any change that:

1. flips a surface toward **Internal / Shadow / Paper / Beta / Production / Institutional**;  
2. changes EngineState semantics, Weight Registry active sets, ORCH DAG edges, or promote-path gates;  
3. dual-writes or replaces Production incumbents (notably E03);  
4. exposes new research data to Beta or public surfaces.

Trivial docs/typos and pure refactors with no flag/behavior change may use a **lite checklist** (§3.4) — still no architecture redesign.

---

# 1. Readiness Philosophy

## 1.1 Deployment principles

| Principle | Meaning |
|-----------|---------|
| Architecture first | Code implements frozen specs; it does not invent layers |
| Evidence over narrative | No Production score/opinion without evidence + confidence |
| Fail closed on safety | E14 promote path, PIT integrity, secrets — never fail open |
| Fail soft on optional voters | Missing E04/E08/E11 ⇒ weight 0 + warning, not crash |
| Shadow before crown | New intelligence runs in shadow before displacing incumbents |
| Flags over forks | Promotion is a flag/routing event, not a silent code path |
| Research only | No BUY/SELL/EXECUTE under E00 §1.5 |
| Reversible by default | Every Production promotion has a tested rollback |

## 1.2 Promotion philosophy

Promotion is **earned**, not scheduled.

```
Development → Internal → Shadow → Paper Trading → Beta → Production → Institutional
```

Each step requires objective §11 gate pass + §14 sign-offs.  
**Calendar pressure never overrides gates.**

## 1.3 Production criteria (definition of Production)

A surface is **Production** only if all are true:

1. Implements a frozen spec path (E00 + ORCH + relevant engine/L4/E10).  
2. Emits schema-valid `EngineState` (or ORCH/control artifacts where applicable).  
3. Passes §4 / §5 / §10 validation applicable to its type.  
4. Meets §7 performance and §6 operational readiness.  
5. Has §8 security + audit.  
6. Has §13 rollback drill evidence.  
7. Has §14 mandatory approvals recorded.  
8. Has §15 Go decision with zero open **Blocker** items.

## 1.4 Rollback philosophy

| Rule | Detail |
|------|--------|
| Instant flag rollback | Primary control — RTO ≤ 15 minutes |
| Last-good current | Failed runs never overwrite Production `current` |
| Incumbent protection | E03 Production UI remains available until L4 superiority vote |
| No forward-fix under incident | Roll back first; redesign only via E00 amendment later |
| Drill required | Rollback must be demonstrated before first Production flip |

---

# 2. Architecture Compliance

## 2.1 Mandatory references

Every implementation PR that touches engines, ORCH, L4, E10, features, scores, or promote paths **must cite** in the PR description:

| Reference | When required |
|-----------|---------------|
| **E00** section IDs | Always for research-platform PRs |
| **ORCH** section IDs | Scheduling, DAG, propagation, flags, failure, APIs/DB for control plane |
| **L4** section IDs | Composite opinion, fusion, shadow, explanation |
| **Relevant E0X / E10 spec** | Engine or portfolio code |
| **IMP-V1** sprint/workstream | Recommended for programme tracking |
| **PRR-V1** gate IDs | Required on promotion PRs / flag flips |

## 2.2 Automatic reject conditions

**Reject (do not merge / do not promote)** if any of the following hold:

| ID | Violation |
|----|-----------|
| A-R1 | New architecture layer, engine ID, or L0–L8 dependency inversion without E00 amendment |
| A-R2 | Raw market I/O inside L4 / ORCH packages (must consume EngineState / registry) |
| A-R3 | Silent Production blend weights (bypasses Weight Registry) |
| A-R4 | Promote path without E14 assess / fail-open E14 |
| A-R5 | BUY/SELL/EXECUTE controls or broker order placement |
| A-R6 | Unregistered features feeding Production engines |
| A-R7 | Look-ahead / PIT violation known and unfixed |
| A-R8 | L4 set as Production primary without §5 superiority pack |
| A-R9 | Experimental artifacts on unmarked public surfaces |
| A-R10 | Missing EngineState `confidence` / `evidence` / `hash` on Candidate+ outputs |

## 2.3 Compliance attestation (PR template fragment)

```markdown
### Architecture compliance
- [ ] E00 sections: …
- [ ] ORCH sections: … (if applicable)
- [ ] L4 / E0X sections: …
- [ ] No A-R1…A-R10 violations
- [ ] Feature flags default safe (off / shadow as required)
```

---

# 3. Code Review Checklist

Reviewers use this checklist on every non-lite PR. Mark **Pass / Fail / N/A**.

## 3.1 Architecture compliance

- [ ] Implements frozen spec; no redesign  
- [ ] Correct layer dependency direction (E00 §2)  
- [ ] Typed contracts only (E00 §5)  
- [ ] ORCH annex updated if new engine/node (ORCH §19)  

## 3.2 Naming

- [ ] Feature/signal IDs match E00 §6–§7  
- [ ] Tables/APIs match E00 §13–§14  
- [ ] Engine IDs immutable (`E01`…`E14`, `L4`, `ORCH`)  

## 3.3 Tests

- [ ] Unit tests for changed logic  
- [ ] Contract/schema fixtures updated  
- [ ] Integration test for ORCH node or API path  
- [ ] Replay/PIT test when features/scores touched  
- [ ] CI green on required suites  

## 3.4 Logging

- [ ] Structured logs with `run_id` / `node_id` / hashes where applicable  
- [ ] No secrets, raw PII, or full vendor payloads  
- [ ] Errors use E00/ORCH error codes  

## 3.5 Performance

- [ ] Latency budget considered (§7)  
- [ ] No unbounded full-universe work on interactive path  
- [ ] Cache TTLs align with ORCH/engine specs  

## 3.6 Security

- [ ] Secrets only in env  
- [ ] AuthZ correct for surface (public/beta/internal/admin)  
- [ ] No privilege escalation via flag/admin APIs  

## 3.7 Documentation

- [ ] PR cites specs  
- [ ] Runbook touch if ops behavior changes  
- [ ] Flag defaults documented  

## 3.8 Backward compatibility

- [ ] Additive schema or versioned shim  
- [ ] Legacy E03/`agi_research_score` path preserved until dual-write parity gate  
- [ ] Consumers not broken without deprecation window  

## 3.9 Lite checklist (docs/refactors only)

- [ ] No behavior/flag/schema change  
- [ ] CI still green  
- [ ] No architecture text presented as normative redesign  

---

# 4. Engine Promotion Checklist

Applies to **E01, E02, E03, E04, E05, E08, E09, E11, E13, E14, E10** (and any future engine after E00 amendment).

Mark each row **Pass / Fail**. Any **Fail** on a mandatory row blocks the target gate.

| ID | Gate item | Mandatory from | Pass criteria |
|----|-----------|----------------|---------------|
| E-U1 | Unit tests | Internal | Critical paths covered; CI green |
| E-I1 | Integration tests | Shadow | ORCH node + DB persist + API read |
| E-R1 | Historical replay | Shadow | PIT fixtures pass; no look-ahead |
| E-B1 | Backtesting pack | Beta (alpha engines); Production for sizing claims | Documented horizon, universe, costs assumptions |
| E-S1 | Statistical validation | Beta→Production | IC/Brier/other per engine spec targets recorded |
| E-C1 | Calibration | Production if probabilistic | `calibration_id` versioned; reliability reviewed |
| E-L1 | Latency | Internal | Job + GET budgets met (engine spec / §7) |
| E-O1 | Observability | Internal | Metrics: latency, stale_ratio, error rate; logs hashed |
| E-F1 | Failure testing | Shadow | Dependency-down / stale / partial data behaviors match spec |
| E-E1 | Evidence packs | Beta promote path | E00 §10 pack present on promoted objects |
| E-G1 | E14 path | Beta/Production promote | Fail-closed proven (`ORCH_E14_REQUIRED` test) |
| E-W1 | Weight Registry | Production blends | No silent hardcodes; `weight_set_id` active |
| E-D1 | Docs / runbook | Production | Owner, flags, rollback, on-call notes |
| E-A1 | Approvals | Per §14 | Sign-offs recorded |

**E03 special rule:** Production technical incumbent may already be live; **contractisation / dual-write** still requires E-U1, E-I1, parity pack, and rollback to legacy worker.

**E14 special rule:** Cannot be “optional” on promote paths; E-G1 is always mandatory for client/CIO promotion.

---

# 5. Composite Promotion (L4 vs E03)

L4 may write **shadow** opinions without replacing E03.  
L4 may **not** become Production primary (`l4_replace_e03_display` / `l4_cio_brief_primary`) until **all** §5 criteria Pass.

## 5.1 Mandatory superiority pack

| ID | Criterion | Pass definition |
|----|-----------|-----------------|
| L4-S1 | Statistical superiority / non-inferiority | Walk-forward Rank IC / agreed KPI **non-inferior** for ≥ **40 sessions**; superiority on pre-registered primary KPI for promotion vote |
| L4-S2 | Calibration superiority | Brier + reliability diagram **not worse** than E03-as-classifier baseline on same labels; slope reviewed |
| L4-S3 | Lower false positives | At agreed decision threshold, false-positive rate ≤ E03 baseline **or** explicitly accepted with lower size via E14 |
| L4-S4 | Stable confidence | Confidence decomposition stable; no pathological conf=1.0 spikes without evidence; fusion_mult audited |
| L4-S5 | Historical robustness | Crisis/neutralisation fixtures behave per E00 §11 / L4 hierarchy (E14/E01 authority) |
| L4-S6 | Explanation completeness | 100% sampled opinions include contributing + conflicting engines |
| L4-S7 | Shadow hygiene | Shadow writes never mutated E03 Production tables |
| L4-S8 | Approvals | Quant + Risk + CIO written vote |

## 5.2 Explicit No-Go examples

- Shadow IC positive in-sample only, failed embargoed OOS  
- Calibration slope ≪ 1 with no remediation  
- E14 missing on any promote sample in audit  
- UI copy implies L4 is Production while flag false  

## 5.3 After promotion

- E03 remains available as voter/engine and rollback incumbent  
- Rollback drill must restore E03-primary display within RTO  

---

# 6. Operational Readiness

## 6.1 Monitoring

Mandatory metrics before Production (ORCH §11, E00 §1.6):

- `orch_node_latency_ms`, `orch_pipeline_blocked`, `orch_stale_ratio`  
- `orch_gate_counts` (E14 blocks, conf haircuts)  
- `orch_contract_fail_total`  
- Engine-specific error rate / stale_ratio  
- L4 `orch_shadow_divergence` while shadow  

## 6.2 Dashboards

| Dashboard | Required before |
|-----------|-----------------|
| ORCH pipeline board | Internal |
| Engine health (E01/E03/E14 minimum) | Shadow |
| L4 shadow vs E03 | Shadow |
| E14 gate / breach | Beta |
| SLO burn | Production |

## 6.3 Alerts

| Alert | Severity | Condition (initial) |
|-------|----------|---------------------|
| EOD seal missed | Sev-1 | No successful critical-path seal by 19:30 IST weekday |
| E14 enforce disabled | Sev-1 | Flag off in Production unexpectedly |
| Contract fail spike | Sev-2 | >N fails/hour |
| Stale E01 | Sev-2 | Weekday stale >6h policy breach |
| API p95 burn | Sev-2 | Warm GET p95 >300ms for 15m |
| Shadow divergence explode | Sev-3 | Divergence > threshold 3 consecutive days |

## 6.4 Health checks

- `GET /api/v1/orch/health` — process up  
- `GET /api/v1/orch/ready` — DB/queue ready  
- `GET /api/v1/orch/status` — per-node last success  

Load balancer / host must use health+ready appropriately.

## 6.5 Runbooks (minimum set)

| Runbook | Exists before |
|---------|---------------|
| EOD seal failure | Internal |
| Vendor outage / degraded mode | Shadow |
| E14 block surge | Beta |
| L4/E03 rollback | Before L4 primary |
| DB degradation | Production |
| Flag mis-flip | Production |

## 6.6 Recovery procedures

Documented in runbooks with:

1. Detect → 2. Mitigate (flag/cache) → 3. Communicate → 4. Recover → 5. Postmortem (Sev-1/2)

---

# 7. Performance Standards

Aligned with ORCH §10 and engine specs. **Fail = over budget without waiver.**

## 7.1 Latency budgets

| Path | p95 target |
|------|------------|
| Warm GET engine/L4/ORCH current | < 300ms |
| Interactive symbol recompute (warm features) | < 8s |
| E14 assess | < 5s |
| L4 fusion per symbol (warm states) | < 2s |
| E01 job | < 45s |
| E14 firm job | < 60s |
| E03 universe job | < 20m |
| EOD critical path seal | ≤ 19:30 IST |

## 7.2 Memory / CPU budgets (guidance caps)

| Node class | Memory cap guidance | CPU |
|------------|---------------------|-----|
| API gateway | ≤ 1GB nominal | burst OK |
| E01/E14 firm | ≤ 2GB | 1–2 cores |
| E02/E03/E13 jobs | ≤ 8GB | 2–4 cores |
| E10 optimiser | ≤ 4GB | 2 cores |

Exceeding caps requires capacity note + approval in PRR pack.

## 7.3 API SLAs

| Class | Availability | Error rate |
|-------|--------------|------------|
| Production research GET | ≥ 99.5% weekdays | < 1% 5xx (ex-vendor) |
| Promote/admin APIs | ≥ 99.0% | < 0.5% unexpected 5xx |

## 7.4 Database SLOs

| Metric | Target |
|--------|--------|
| Primary DB availability | ≥ 99.5% |
| Migration expand/contract safe | Zero downtime for Production currents |
| PIT query correctness | 100% on release suite |

---

# 8. Security

## 8.1 Secrets

- [ ] No secrets in git, images, logs, or client bundles  
- [ ] Vendor keys only in server/engine environment  
- [ ] Rotation path documented for Production keys  

## 8.2 Authentication

| Surface | Requirement |
|---------|-------------|
| Public | Existing site controls; no admin |
| Beta | PIN/SSO |
| Internal CIO / ORCH admin | Role-gated SSO (or equivalent) + MFA preferred |
| Flag flip / promote | Authenticated + audited + dual control for Production |

## 8.3 Audit logs

Mandatory audit for:

- feature flag changes  
- Weight Registry activation  
- promote decisions  
- E14 block overrides (if any; default none)  
- snapshot seals  

Retention ≥ 1 year.

## 8.4 Access control

- [ ] RLS / least privilege on research tables (E00 §13.6)  
- [ ] Service role write separated from read roles  
- [ ] Experimental data not readable on public roles  

**Fail closed:** missing auth on admin routes is a Blocker.

---

# 9. Data Quality

## 9.1 Completeness

| Check | Pass |
|-------|------|
| Critical feature coverage | Meets engine floor or engine enters degraded with warnings |
| Universe membership | as_of join; no silent survivorship expansion |

## 9.2 Freshness

| Dataset class | Policy |
|---------------|--------|
| E01 macro | Weekday stale >6h → degraded path (E00 §4.3) |
| E03 daily scores | Prior close allowed only with stale warning if session miss |
| E14 promote assess | Must be current for object_hash |

## 9.3 Point-in-time validation

- [ ] `available_at ≤ as_of` enforced in builders  
- [ ] Replay `pit_mode=true` disables latest caches  
- [ ] CI fixtures for future-dated joins fail closed  

## 9.4 Missing data handling

- [ ] Never silent zero for optional upstream (E00 §5.2)  
- [ ] `stale_inputs` / `missing_data` evidence populated  
- [ ] Optional voter absence ⇒ weight 0  

## 9.5 Fallback behaviour

Documented per engine; Production fallbacks must be:

1. last good current (if policy allows), else  
2. degraded explicit state, else  
3. fail closed (safety paths)

Invented regimes/scores are **forbidden**.

---

# 10. Backtesting Readiness

Required for alpha engines and for any Production claim about expected performance quality.

| ID | Control | Pass criteria |
|----|---------|---------------|
| BT-W1 | Walk-forward | Expanding/rolling windows with embargo |
| BT-O1 | Out-of-sample | Pre-registered OOS period; no peeking |
| BT-C1 | Transaction costs | Gross and net reported; conservative defaults |
| BT-L1 | Look-ahead bias | PIT tests green; no future joins |
| BT-S1 | Survivorship bias | Universe membership as_of |
| BT-P1 | Capacity | ADV/participation assumptions stated; E14 liquidity aware |
| BT-R1 | Reproducibility | `snapshot_id` / hashes / `weight_set_id` / `calibration_id` recorded |

**Paper trading** (IMP Phase 4) supports operational readiness but does **not** alone satisfy BT-* for L4 primary promotion — §5 statistical pack still required.

---

# 11. Release Gates

Objective pass/fail per stage. **All mandatory rows Pass** to enter the stage.

## 11.1 Development

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-D1 | Builds in CI | |
| G-D2 | Unit tests for changed code | |
| G-D3 | Architecture citations present | |
| G-D4 | Flags default safe (off/shadow) | |

## 11.2 Internal

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-I1 | Integration path works in internal env | |
| G-I2 | Logging + basic metrics | |
| G-I3 | Auth gated to internal roles | |
| G-I4 | Latency smoke within 1.5× budget | |

## 11.3 Shadow

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-S1 | Shadow writes isolated (no Production current clobber) | |
| G-S2 | Replay/PIT smoke green | |
| G-S3 | Failure tests for missing optional deps | |
| G-S4 | Divergence/health dashboard live | |
| G-S5 | E03 Production UI unchanged (for L4/E10 migrations) | |

## 11.4 Paper Trading

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-P1 | No broker/order APIs | |
| G-P2 | Immutable fill ledger + research disclaimer | |
| G-P3 | Costs applied (net vs gross) | |
| G-P4 | E14 assess on paper books | |

## 11.5 Beta

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-B1 | Watermarks RESEARCH/SHADOW correct | |
| G-B2 | Evidence + confidence visible | |
| G-B3 | Rate limits + cache configured | |
| G-B4 | E14 fail-closed on promote samples | |
| G-B5 | Statistical pack attached for alpha surfaces | |

## 11.6 Production

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-Pr1 | All applicable §4 engine checklist Pass | |
| G-Pr2 | §6 operational readiness Pass | |
| G-Pr3 | §7 performance Pass | |
| G-Pr4 | §8 security Pass | |
| G-Pr5 | §9 data quality Pass | |
| G-Pr6 | §13 rollback drill Pass (≤15m flag RTO) | |
| G-Pr7 | §14 sign-offs complete | |
| G-Pr8 | §15 Go with zero Blockers | |
| G-Pr9 | If L4 primary: §5 all Pass | |

## 11.7 Institutional

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| G-In1 | Production stable ≥ soak window (IMP hypercare class) | |
| G-In2 | Multi-engine voter set gate packs signed | |
| G-In3 | Warehouse/retention policy enforced | |
| G-In4 | Institutional API access controls + audit | |
| G-In5 | Advanced L8 SLO board live | |

---

# 12. Failure Scenarios

Each scenario requires a documented expected behavior + test or drill evidence before Production.

| ID | Scenario | Expected system behavior | Evidence |
|----|----------|--------------------------|----------|
| F1 | Market crash / crisis regime | E01 crisis axes; E14 hard_derisk/playbooks; L4 hierarchy haircuts; E04 MR disabled as specified | Fixture + shadow replay |
| F2 | Missing data | Degraded + warnings; no fabrication; optional voter weight 0 | Chaos test |
| F3 | Vendor/API outage | Retries then quarantine/degraded; last-good policy per node | Drill |
| F4 | Database outage | ready fails; no split-brain writes; alert Sev-1 | Drill |
| F5 | Engine failure | Blocking deps stop dependents; unrelated parallel continues; last-good current preserved | ORCH integration test |
| F6 | Conflicting signals | L4 conflict ledger; Neutral preferred when hierarchy demands; contradictions surfaced | L4 fixtures |
| F7 | High volatility | E14/E01 vol paths; E10 size/vol targets reduce; alerts | Fixture |
| F8 | ORCH DAG timeout | Barrier fail; pipeline_blocked metric; specialised shed | Test |
| F9 | Flag mis-flip | Audit + dual control; immediate rollback runbook | Drill |
| F10 | PIT violation detected | Fail closed Production/replay; no publish | CI |

---

# 13. Rollback Plan

## 13.1 Immediate rollback (Production incident)

1. Flip routing flags to last-known-good (`orch_feature_flags`).  
2. Confirm E03-primary / prior DAG version serving.  
3. Announce status to CIO/Eng.  
4. Freeze promotes.  
5. Open incident; postmortem for Sev-1/2.

**RTO target:** ≤ **15 minutes** (flag-only).

## 13.2 Shadow rollback

- Disable `*_shadow_write` or stop shadow consumer UI.  
- Retain shadow tables for forensics.  
- Production currents untouched.

## 13.3 Engine rollback

- Pin previous `model_version` / worker image.  
- Restore `current` pointer only from last good snapshot if corrupted.  
- Keep dual-write legacy worker for E03 until parity re-proven.

## 13.4 Feature flag rollback

- Preferred mechanism for all opinion/UI/portfolio exposure changes.  
- Every Production flag change must list **rollback flag values** in the PRR pack.

## 13.5 Database rollback

- Prefer expand/contract migrations — avoid destructive rollback.  
- If bad write: restore from snapshot / recompute from PIT, not blind UNTABLE.  
- Never delete audit/flag audit rows.

## 13.6 Rollback drill evidence (mandatory pre-Production)

| Drill | Pass |
|-------|------|
| Flag rollback to E03-primary | ≤15m, verified UI/API |
| Disable new engine UI flag | Surface gone; APIs safe |
| Pin prior `orch_dag_version` | Seal uses prior edges |

---

# 14. Sign-off Matrix

Approvals recorded in the PRR pack (ticket/PR comment with name, role, timestamp, gate stage).

| Gate stage | Architecture | Engineering | Research (Quant) | Risk | Data | Operations |
|------------|--------------|-------------|------------------|------|------|------------|
| Development merge | Review if contracts/DAG | **Required** | Optional | Optional | Optional | Optional |
| Internal enable | Optional | **Required** | Recommended | Optional | Optional | Recommended |
| Shadow enable | **Required** if DAG/L4/weights | **Required** | **Required** | Recommended | Recommended | **Required** |
| Paper Trading enable | Optional | **Required** | **Required** | **Required** | Optional | **Required** |
| Beta enable | **Required** | **Required** | **Required** | **Required** | **Required** | **Required** |
| Production enable | **Required** | **Required** | **Required** | **Required** | **Required** | **Required** |
| L4 replaces E03 | **Required** | **Required** | **Required** | **Required** | Recommended | **Required** + **CIO** |
| Institutional | **Required** | **Required** | **Required** | **Required** | **Required** | **Required** + **CIO** |

**Notes:**

- **Risk** has veto on promote-path and E14-related changes.  
- **CIO** required for L4 primary and Institutional.  
- Architecture sign-off attests “no E00 amendment required / or amendment merged.”  

---

# 15. Go / No-Go Decision

## 15.1 Final Production checklist (mandatory)

Copy into every Production promotion pack. All must be **Pass** (or formal waived with Risk+Eng+CIO for non-safety items only). **No waivers** for A-R*, E-G1, PIT, secrets, or L4-S* when L4 primary.

### A. Architecture & programme

- [ ] E00 / ORCH / L4 / engine citations complete  
- [ ] No A-R1…A-R10 violations  
- [ ] IMP-V1 work item referenced (recommended)  

### B. Code & contracts

- [ ] §3 code review checklist Pass  
- [ ] EngineState/schema contract tests Pass  
- [ ] Backward compatible or shim versioned  

### C. Engine / composite validation

- [ ] §4 engine checklist Pass for engines in scope  
- [ ] If L4 primary: §5 L4-S1…L4-S8 Pass  
- [ ] §10 backtesting readiness Pass where applicable  

### D. Data & quality

- [ ] §9 completeness/freshness/PIT/missing/fallback Pass  

### E. Security

- [ ] §8 secrets/auth/audit/ACL Pass  

### F. Performance

- [ ] §7 latency/memory/API/DB Pass  

### G. Operations

- [ ] §6 monitoring/dashboards/alerts/health/runbooks Pass  
- [ ] Failure scenarios F1–F10 addressed with evidence  

### H. Rollback

- [ ] §13 drill Pass; rollback flag values documented  

### I. Approvals

- [ ] §14 sign-offs complete for Production (and CIO if required)  

### J. Decision

- [ ] **GO** — promote flags  
- [ ] **NO-GO** — list Blockers below  

## 15.2 Decision record template

```markdown
# PRR Decision Record
- Change: …
- Target gate: Production | Beta | …
- Spec refs: E00 …; ORCH …; L4/E0X …
- Gate report IDs: …
- Rollback values: …
- Blockers open: none | …
- Decision: GO | NO-GO
- Sign-offs: Architecture …; Engineering …; Research …; Risk …; Data …; Operations …; CIO …
- Timestamp (IST): …
```

## 15.3 Binding rule

> **Nothing reaches Production until every mandatory item Passes.**  
> Architecture is complete. After PRR-V1, work is implementation, testing, validation, backtesting, and operations — not new architecture — unless approved through the E00 amendment process.

---

# 16. PRR process mechanics

## 16.1 When to run a full PRR

- First enablement of a gate stage for a surface  
- L4 primary vote  
- ORCH DAG version change affecting critical path  
- Weight Registry activation affecting Production blends  
- Any incident-driven emergency change (retroactive PRR within 5 business days)

## 16.2 Evidence pack contents

1. PR links + spec citations  
2. CI links  
3. Gate report IDs (validation/calibration)  
4. Dashboard screenshots or metric queries  
5. Rollback drill notes  
6. Sign-off record  

Store under `prr_packs/` or equivalent issue attachments; link from flag audit.

## 16.3 Lite vs full

| Change type | Review |
|-------------|--------|
| Docs-only / non-behavioral refactor | §3.9 lite |
| New shadow engine write | Full through Shadow |
| Beta/Production flag flip | Full through target gate |
| Architecture amendment | **E00 process first**, then PRR |

---

# 17. Relationship to frozen corpus

| Frozen document | PRR uses it for |
|-----------------|-----------------|
| E00 | Law, contracts, lifecycle, research-only |
| ORCH | DAG, failure, flags, SLOs, observability |
| L4 | Composite shadow/primary rules |
| E0X / E10 | Engine-specific budgets and behaviors |
| IMP-V1 | Scheduling of when gates are attempted |

PRR does **not** replace those documents; it **authorizes promotion** against them.

---

# 18. Document control

| Version | Notes |
|---------|-------|
| 1.0.0 | Initial binding Production Readiness Review under Architecture v1.0 Complete |

**Architecture closure statement:**  
With PRR-V1 published, the Architecture v1.0 document set is **complete**. Further normative architecture requires E00 amendment. Day-to-day delivery follows IMP-V1 under this PRR.

---

*End of PRODUCTION READINESS REVIEW V1 — final governance gate for AGI Investment Office*
