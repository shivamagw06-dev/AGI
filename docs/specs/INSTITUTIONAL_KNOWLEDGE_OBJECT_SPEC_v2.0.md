# AGI Institutional Knowledge Object Specification v2.0

**Document type:** Engineering Specification  
**Layer:** Institutional Knowledge Layer  
**Status:** Core Platform — canonical pre-code specification  
**Supersedes:** Field-centric Company DNA v1.x, question-only DNA drafts  

---

## Mission

The **Institutional Knowledge Object (IKO)** is AGI's permanent, evidence-backed institutional understanding of a listed company.

IKO is **not**:

- A financial statement warehouse
- An annual report summary
- A research note generator
- A database of answers to questions

IKO **is**:

- A **database of evidence-backed institutional claims**
- The permanent knowledge object every intelligence engine, workflow, and Investment OS consumes
- Institutional memory that evolves continuously as evidence changes

**Company DNA** is the company-scoped implementation of IKO.

---

## Fundamental design principle

> **Don't make Company DNA a database of answers. Make it a database of evidence-backed institutional claims.**

Institutional investors think in **beliefs**, not questions.

| Questions retrieve | Claims store |
|--------------------|--------------|
| "What is TCS's moat?" | "TCS possesses durable switching costs with large enterprise clients." |
| "Is TCS expensive?" | "Current valuation is near the 5-year median P/E." |
| "Should I buy TCS?" | Assembled from relevant claims across Business, Financial, Valuation, Risk, Thesis |

**Evaluation test for every future feature:**

> Does this help IKO maintain, validate, or assemble claims better?

If yes → belongs in IKO / Company DNA.  
If no → belongs in Evidence Graph, Decision Memory, Forecast Engine, Monitoring Engine, or Investment OS.

---

## Architecture

```text
Evidence
  ↓
Claims                    ← atomic unit of institutional knowledge
  ↓
Institutional Knowledge Object (Company DNA for equities)
  ↓
Research Workflow
  ↓
Decision Memory           ← versions claims, not prose
  ↓
Investment OS             ← reasons over claims
  ↓
Response                  ← assembles claims into institutional research
```

**Ask pipeline (claim-centric):**

```text
User Question
  ↓
Intent Resolution
  ↓
Decision Objective
  ↓
Relevant Claim Selection   ← not free-text search
  ↓
Evidence Validation
  ↓
Confidence
  ↓
Reasoning
  ↓
Research Conclusion
  ↓
Response
```

---

## Claim model

### Claim object (canonical)

Every institutional belief is stored as a **Knowledge Claim**:

```yaml
claim_id: CLAIM_TCS_SWITCHING_COSTS_001
entity_id: TCS
entity_type: company

statement: >
  TCS possesses durable switching costs with large enterprise clients.

claim_type: business
category: competitive_position
subcategory: switching_costs

state: SUPPORTED          # see Claim States below
confidence: 91            # evidence reliability, not expected return

evidence_refs:
  - evidence_id: EV_AR_2025_CLIENT_RETENTION
    source: annual_report
    as_of: 2025-03-31
    coverage: client_retention_disclosure
  - evidence_id: EV_MARGIN_STABILITY_5Y
    source: financial_intelligence
    as_of: 2026-08-01

contradictions:
  - claim_id: CLAIM_TCS_PRICING_PRESSURE_002
    severity: watch

dependencies:
  - claim_id: CLAIM_TCS_ENTERPRISE_MIX_003

monitoring:
  trigger: "Operating margin < 22% OR client churn > 5%"
  status: healthy
  last_checked: 2026-08-05

reasoning_summary: >
  Retention rates and margin stability support switching-cost durability;
  pricing pressure claim partially offsets conviction.

owner: company_dna
last_review: 2026-08-05T00:00:00Z
version: 3
fabricated: false
llm_used: false
```

### Claim states

| State | Meaning |
|-------|---------|
| `SUPPORTED` | Evidence-backed; high confidence; actively maintained |
| `ANSWERED` | Directionally known; sufficient for research but not fully validated |
| `PARTIAL` | Known with material gaps |
| `CONTRADICTED` | Conflicting evidence; requires resolution |
| `STALE` | Previously supported; evidence aged beyond threshold |
| `UNKNOWN` | Not yet researched; explicitly open |
| `UNDER_REVIEW` | Active reassessment in progress |

**Note:** `SUPPORTED` is stronger than `ANSWERED`. Institutional research is about evidence, not completion.

---

## Claim types

| Type | Example |
|------|---------|
| `business` | TCS benefits from switching costs with enterprise clients. |
| `financial` | Cash generation remains strong relative to capex needs. |
| `management` | Capital allocation has historically been disciplined. |
| `valuation` | Current valuation is near the 5-year historical median. |
| `growth` | Future growth depends on digital deal expansion. |
| `risk` | AI pricing pressure may compress margins over time. |
| `investment` | Future returns depend more on earnings growth than multiple expansion. |
| `monitoring` | Operating margin should remain above 22%. |
| `thesis` | Institutional thesis favors quality franchise over cyclical recovery. |

---

## Claim registry

The **Claim Registry** defines required institutional claims per entity type.

Structure:

```text
Claim Template
  ↓
Category (identity, business, competitive, financial, …)
  ↓
Required / Optional
  ↓
Evidence requirements
  ↓
Monitoring trigger (optional)
  ↓
Dependencies (optional)
```

Company-scoped IKO instances **instantiate** registry templates into live claims.

### Required claim categories (company)

Claims must exist (or be explicitly `UNKNOWN`) across:

1. **Identity** — what the company is, who it serves, how it makes money  
2. **Business Model** — revenue drivers, margin drivers, scalability  
3. **Economic Engine** — ROIC, ROE, FCF, capital intensity  
4. **Competitive Position** — moat sources, durability, threats  
5. **Management** — capital allocation, execution, alignment  
6. **Financial Quality** — margins, cash, leverage, resilience  
7. **Growth** — sources, limits, structural vs cyclical  
8. **Valuation Context** — vs history, peers, growth, risk, expectations priced in  
9. **Investment Thesis** — own/avoid rationale, assumptions, invalidation criteria  
10. **Risks** — business, financial, industry, macro, execution, governance  
11. **Monitoring** — KPIs, events, reassessment triggers  

Each category contains **claim templates**, not free-text fields.

---

## Institutional Knowledge Object structure

```text
InstitutionalKnowledgeObject
├── identity                 # entity metadata (ticker, ISIN, sector, …)
├── claims[]                 # all Knowledge Claims
├── evidence_refs[]          # pointers into Evidence Graph (not copies)
├── unknowns[]               # explicit open claims / gaps
├── monitoring[]             # claim-linked triggers
├── decision_memory_refs[]   # claim version history pointers
├── completeness             # claim-state counts (not percentages)
├── version_history[]        # append-only audit trail
└── metadata                 # owner, timestamps, coverage grades
```

**Company DNA** = `InstitutionalKnowledgeObject` where `entity_type = company`.

---

## What IKO answers

IKO does not answer literal user questions. It answers:

| Query | IKO response |
|-------|--------------|
| Which claims are currently believed? | Claims in `SUPPORTED` or `ANSWERED` |
| Which are uncertain? | Claims in `PARTIAL`, `UNKNOWN`, `UNDER_REVIEW` |
| Which changed recently? | Decision Memory delta on claim confidence/state |
| Which are contradicted? | Claims in `CONTRADICTED` + contradiction graph |
| Which need investigation? | `UNKNOWN` + workflow next-best-claim |
| What should be monitored? | Claims with active monitoring triggers |

User-facing Ask assembles relevant claims into institutional research prose.

---

## Evidence Graph relationship

**Wrong:** `Company → Evidence`

**Correct:**

```text
Evidence → supports/contradicts → Claim → informs → Decision
```

Evidence Graph stores raw and derived evidence.  
Claims reference evidence by ID.  
Responses never invent evidence not linked to a claim.

Every claim must answer: **Why do we believe this?**

---

## Decision Memory relationship

Decision Memory versions **claims**, not prose theses.

```yaml
decision_memory_entry:
  claim_id: CLAIM_TCS_VALUATION_004
  prior_state: PARTIAL
  new_state: SUPPORTED
  prior_confidence: 62
  new_confidence: 78
  evidence_delta:
    added: [EV_PEER_COMP_2026Q2]
  reason: Peer-relative valuation context completed
  timestamp: 2026-08-05T14:00:00Z
```

Audit trail: which belief changed, why, on what evidence, when.

---

## Monitoring relationship

Monitoring attaches to **claims**, not generic KPI lists.

```yaml
claim_id: CLAIM_TCS_MARGIN_RESILIENCE_005
statement: Operating margins remain resilient.
monitoring:
  trigger: operating_margin < 22%
  status: healthy
  last_value: 24.1%
  last_checked: 2026-08-05
```

When a trigger fires → claim state moves to `UNDER_REVIEW` or `CONTRADICTED` → workflow reassessment.

---

## Research Workflow integration

Workflows **retrieve and update claims**, not fill text sections.

| Workflow step | Claim action |
|---------------|--------------|
| Business Quality Assessment | Read/update `business`, `competitive_position` claims |
| Valuation Review | Read/update `valuation` claims |
| Risk Assessment | Read/update `risk` claims |
| Thesis Review | Read/update `investment`, `thesis` claims |

Research Status (✓ / ⚠ / □) maps to claim states — **no percentages**.

---

## Completeness metric

```yaml
completeness:
  required_claims: 47
  supported: 18
  answered: 9
  partial: 6
  contradicted: 2
  stale: 1
  unknown: 9
  under_review: 2
```

Institutional analysts complete research — they do not complete percentages.

---

## Update policy

IKO is **never rewritten**. Every update creates:

```yaml
version_entry:
  version: 4
  timestamp: 2026-08-05T14:00:00Z
  reason: Q1 earnings update
  evidence_refs: [EV_RESULTS_Q1_2026]
  prior_state: { ... }
  new_state: { ... }
  changed_claim_ids: [CLAIM_TCS_MARGIN_005]
```

All changes are auditable.

---

## Ingestion contract (who writes claims)

| Writer | Trigger | Updates |
|--------|---------|---------|
| Evidence pipeline | New filing, earnings, news | Financial, risk claims + evidence refs |
| Claim extractor | Document intelligence (IKL) | Business, management claims from filings |
| Workflow engine | Research step completed | Relevant category claims + state transition |
| Decision Memory | Thesis/confidence change | Claim version + decision_memory_ref |
| Monitoring engine | Trigger evaluation | Monitoring status, stale/contradicted flags |
| Valuation engine | Multiple refresh | Valuation claims |
| Manual analyst override | Explicit correction | Any claim + version entry |

**Rule:** No engine writes free-text into IKO. All writes are claim create/update with evidence refs.

---

## Validation

IKO is valid only if:

1. Every required claim template is instantiated OR explicitly `UNKNOWN`
2. Every `SUPPORTED` claim has ≥1 evidence ref with source, date, coverage
3. Every `CONTRADICTED` claim lists contradiction refs
4. No claim lacks a `claim_type` and `category`
5. No hidden assumptions — gaps live in `unknowns[]`
6. Confidence explains evidence reliability, not expected return
7. No BUY/SELL/target language in claim statements

Failure mode: `Needs Further Investigation` at workflow level.

---

## API contracts (v1)

### Read

```
GET /v1/iko/company/{ticker}
GET /v1/iko/company/{ticker}/claims
GET /v1/iko/company/{ticker}/claims/{claim_id}
GET /v1/iko/company/{ticker}/claims?state=CONTRADICTED
GET /v1/iko/company/{ticker}/completeness
```

### Write (internal engines only)

```
POST /v1/iko/company/{ticker}/claims          # create claim
PATCH /v1/iko/company/{ticker}/claims/{id}     # update state/confidence/evidence
POST /v1/iko/company/{ticker}/claims/{id}/review
```

### Ask integration

```
resolve_relevant_claims(question, ticker) → claim_ids[]
assemble_response(claims[]) → institutional research (Response Constitution)
```

---

## Migration from existing systems

| Existing | Migration path |
|----------|----------------|
| `cid/` dossier sections | Map sections → claim templates; CID becomes IKO persistence adapter |
| `institutional_knowledge_layer/` slots | Slot extractions → claim creates with evidence refs |
| `app/iie/` DNA dimensions | Dimension assessments → typed claims with confidence |
| `company_memory/` (KC.1) | Time-series feed monitoring triggers; not primary claim store |
| `thesis_engine/thesis_dna/` | Deprecate hardcoded traits → investment/thesis claims |

**Target:** Single canonical store at `institutional_knowledge_object/` with CID as compatibility layer during migration.

---

## Acceptance tests

| Test | Pass criteria |
|------|---------------|
| Claim required | Every registry template has instance or `UNKNOWN` |
| Evidence linked | `SUPPORTED` claims have evidence refs |
| No orphan evidence | Evidence Graph nodes link to ≥0 claims or marked raw |
| Contradiction explicit | Conflicting claims reference each other |
| Decision auditable | Every confidence change has Decision Memory entry |
| Monitoring wired | Monitoring triggers linked to claims |
| Ask claim assembly | "Should I buy TCS?" resolves business/financial/valuation/risk/thesis claims |
| No advice language | Validation rejects BUY/SELL/target in claim statements |
| Staleness detected | Claims past review threshold marked `STALE` |

---

## Success metric

An institutional analyst opens Company DNA (IKO) and immediately understands:

- What claims AGI currently believes about the business
- Which claims are supported, uncertain, or contradicted
- What evidence supports each belief
- What changed and why
- What remains unknown
- What to research next

Without reading hundreds of pages of primary sources.

---

## What comes next (engineering, not philosophy)

This spec is the last governance document. Next artifacts are **build specs**:

| Spec | Purpose |
|------|---------|
| `Investment_OS_Spec.md` | Decision layer over claims |
| `Decision_Memory_Spec.md` | Claim versioning |
| `Evidence_Graph_Spec.md` | Evidence → Claim edges |
| `Monitoring_Engine_Spec.md` | Trigger evaluation |
| `Sector_DNA_Spec.md` | Sector-scoped IKO |

Implementation order:

1. `institutional_knowledge_object/schema.py` — claim registry + states (done)  
2. `institutional_knowledge_object/store.py` — persistent claim store  
3. CID → IKO migration adapter  
4. Workflow → claim writeback  
5. Ask → claim assembly  

---

## Appendix: Example Ask assembly

**User:** Should I buy TCS?

**AGI internal:**

```text
Decision objective: Evaluate Investment Opportunity
Relevant claims:
  - CLAIM_TCS_SWITCHING_COSTS (business, SUPPORTED, 91)
  - CLAIM_TCS_CASH_GENERATION (financial, SUPPORTED, 88)
  - CLAIM_TCS_VALUATION_MEDIAN (valuation, PARTIAL, 65)
  - CLAIM_TCS_AI_PRICING_RISK (risk, CONTRADICTED, 52)
  - CLAIM_TCS_THESIS_QUALITY (investment, ANSWERED, 74)
```

**Response:** Assembles claims into institutional research (never BUY/SELL).  
**Next best research:** Resolve valuation claim + AI pricing contradiction via peer comparison claims.

---

*Institutional Knowledge Object v2.0 — claim-centric, evidence-backed, auditable.*
