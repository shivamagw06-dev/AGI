# AGI V1.1.1 — Institutional Evidence Platform (IEP-01)

## Mission

> **AGI is an Institutional Knowledge Platform that continuously acquires, validates, normalizes, versions, and preserves institutional evidence, transforming raw market information into a canonical knowledge base from which research, investment decisions, portfolio intelligence, and future AI capabilities are derived. Every material conclusion must be explainable, reproducible, and traceable to primary evidence.**

### Mindset shift

| Today | Target |
|-------|--------|
| Intelligence platform with data feeding engines | **Knowledge platform** — durable institutional knowledge; engines consume it |

Intelligence is a consumer of evidence — not a substitute for it.

## Knowledge OS pipeline

```text
External Provider
        │
        ▼
Data Governance          ← Layer 0
        │
        ▼
Evidence Acquisition
        │
        ▼
Canonical Normalization  ← domain models (not provider payloads)
        │
        ▼
Data Quality Engine      ← score 0–100; DO NOT PUBLISH below threshold
        │
        ▼
Evidence Registry
        │
        ▼
Company Memory + Timeline
        │
        ▼
Evidence Graph + Claims
        │
        ▼
Knowledge Graph → Financial Intelligence
        │
        ▼
Decision Eligibility → Decision Engine
        │
        ▼
Research Lifecycle → Publishing
```

**Not:** `Raw Data → LLM → Research Note`

## Design principles

1. No research without evidence
2. No recommendation without canonical financial statements
3. No narrative without lineage
4. Every material claim maps to primary evidence
5. Missing evidence blocks publication
6. Single canonical Research Pack for all consumers
7. Nothing enters AGI without data governance
8. Every document references an immutable Entity ID (`AGI-COMPANY-NNNNNNN`)

## Package

`intelligence-engine/institutional_evidence/`

| Module | Role |
|--------|------|
| `governance/` | Layer 0 — provider, license, authority, SLA, hash, version, retry, provenance |
| `acquisition/` | Collect docs (entity_id + governance on every document) |
| `canonical/` | Financial statements + domain models (Company, Market, Actions, …) |
| `quality/` | Evidence Quality Score 0–100 |
| `entity/` | Entity resolution bridge (never guess) |
| `registry/` | Immutable evidence objects |
| `company_memory_bridge/` | Persistent memory view |
| `timeline/` | Company history across time |
| `evidence_graph/` | Evidence → claim → consumer lineage |
| `claims/` | Claim objects with confidence / verified |
| `decision_eligibility/` | Earn permission before recommending |
| `learning/` | Continuous evidence learning loop |
| `lifecycle/` | Draft → review → published → stale → refresh |
| `observability/` | Research-quality metrics for Mission Control |
| `research_pack/` / `validator/` / `readiness/` / `orchestrator/` | Pack contract + gates |
| `phase1_acceptance.py` | Explicit Institutional Coverage Complete criteria |

## Canonical domain models

`CanonicalCompany` · `CanonicalFinancialStatements` · `CanonicalMarketData` · `CanonicalCorporateActions` · `CanonicalShareholding` · `CanonicalManagementGuidance` · `CanonicalTranscript` · `CanonicalNewsEvent` · `CanonicalMacroSeries` · `CanonicalValuation` · `CanonicalForecast`

## Soft gates

- **Writer** — requires `claim_safe`
- **Decision Eligibility → Decision** — BUY/SELL/OW/UW only when eligible; else `NO RECOMMENDATION` / `MONITOR`
- **Publishing** — requires claim_safe + Research Ready + quality ≥ threshold

## Institutional APIs

Prefix: `/v1/iep/*` (BFF: `/api/intelligence/iep/*`)

```text
GET /iep/company/{id}
GET /iep/company/{id}/memory
GET /iep/company/{id}/financials
GET /iep/company/{id}/evidence
GET /iep/company/{id}/timeline
GET /iep/company/{id}/research-ready
GET /iep/company/{id}/claims
GET /iep/company/{id}/valuation
GET /iep/company/{id}/knowledge
```

Also: `/iep/entity/{q}`, `/iep/eligibility/{t}`, `/iep/quality/{t}`, `/iep/learn/{t}`, `/iep/lifecycle/{t}`, `/iep/observability`, `/iep/coverage/{t}`

Ask AGI consumes the same APIs. (`/v1/evidence/*` remains IERE.)

## Phase 1 — Institutional Coverage Complete

Top 20 India. For **each** company, all must pass:

- 10+ years financial statements · annual reports · quarterly history
- Earnings presentations · transcripts · corporate actions · shareholding · segments
- Company timeline · canonical financials · company memory · evidence registry · KG
- Research readiness ≥ target · zero unsupported material claims · reproducible note

Only then expand toward Nifty 500.

## Continuous learning

On new filing / transcript / guidance / corp action / rating change:

`Acquire → Normalize → Update Memory → Recompute KG → Refresh FI → Refresh Watchlists → Invalidate stale research → Notify analysts`

## Research lifecycle

`Draft → Analyst Review → Published → Evidence Changes → Marked Stale → Auto Refresh → Republished`

## Related fix

FSE `nse_xbrl` extract accepts `quarter_history` / `annual_history`.
