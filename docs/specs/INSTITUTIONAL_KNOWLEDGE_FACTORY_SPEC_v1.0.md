# AGI Knowledge Production Engine (KPE) v1.0

**Document type:** Engineering Specification  
**Layer:** Knowledge Production Layer  
**Status:** Core Intelligence System  
**Architecture Freeze:** v1.0 — see `docs/ARCHITECTURE_FREEZE_v1.0.md`

> **Note:** `institutional_knowledge_factory` is the legacy module name. KPE (Knowledge Production Engine) is the canonical name. IKC (Compiler) is **Compile Mode** — not a separate system.

---

## Mission

The **Knowledge Production Engine (KPE)** continuously transforms raw and existing financial intelligence into validated institutional knowledge.

AGI does not become smarter because it has more data. AGI becomes smarter because it continuously converts evidence into institutional knowledge.

---

## Two execution modes — one engine

| Mode | Function | When |
|------|----------|------|
| **Compile** | `compile_company()` | First population, rebuild, migration, repair |
| **Incremental** | `process_evidence()` | Earnings, filings, news, live updates |

There is **one production engine**. Not separate Factory and Compiler architectures.

---

## Compile Mode pipeline

```text
Collect → Normalize → Merge → Resolve Duplicates → Resolve Contradictions
→ Identify Assertions → Score → Link Evidence → Generate Company DNA
→ Generate Monitoring → Generate Thesis → Update Knowledge Object
```

Input sources: IKT, Knowledge Factory objects/packs, company seeds, evidence packs.

---

## Incremental Mode pipeline

```text
Collect → Normalize → Extract → Identify Claims → Validate Evidence
→ Resolve Contradictions → Update Assertions → Update Company DNA
→ Update Monitoring → Version Decision Memory → Notify Research Workflows
```

Implementation: `institutional_knowledge_factory/pipeline.py`

---

## Purpose

KPE answers one question:

> How does AGI continuously improve its understanding of every listed company?

```text
Raw Evidence / Existing Stores
  ↓
Knowledge Assertions
  ↓
Institutional Knowledge Objects (IKO)
  ↓
Research Intelligence
  ↓
Investment Intelligence
```

---

## Position in architecture

```text
Evidence Sources
  ↓
Evidence Graph (refs)
  ↓
Knowledge Production Engine (KPE)
  ├── Compile Mode
  └── Incremental Mode
  ↓
Institutional Knowledge Objects (IKO)
  ↓
Institutional Knowledge Runtime (IKR)
  ↓
Research Workflows → Institutional Research Engine (IRE) → Response
```

KPE **writes** knowledge (via approved writers). IKR **validates** knowledge at read time. LLMs are never writers.

---

## Input sources

| Source type | Trust baseline |
|-------------|----------------|
| `annual_report` | 90 |
| `quarterly_results` | 85 |
| `investor_presentation` | 80 |
| `conference_call` | 75 |
| `corporate_filing` | 88 |
| `exchange_announcement` | 82 |
| `shareholding_data` | 85 |
| `financial_statement` | 90 |
| `consensus_estimate` | 70 |
| `historical_price` | 75 |
| `corporate_action` | 85 |
| `macro_data` | 80 |
| `sector_data` | 78 |
| `alternative_data` | 65 |
| `analyst_research` | 72 |

Every source receives: `source_id`, `timestamp`, `trust_score`, `coverage`, `freshness`.

Compile mode additionally consumes: IKT facts, KF company objects, KF evidence packs, decision quality records.

---

## Claim generation

KPE never stores raw documents as knowledge. It extracts institutional assertions.

Every assertion must contain:

- Statement  
- Evidence refs  
- Confidence  
- Dependencies  
- Monitoring rules  
- Review date  

Assertions without evidence remain `UNKNOWN`.

---

## Company DNA update

Company DNA is never rewritten. It evolves.

Every update records:

- Previous assertion  
- New assertion  
- Evidence added / removed  
- Reason  
- Timestamp  
- Confidence change  
- Impact  

Implementation uses IKR `update_assertion()` with writer `evidence_pipeline`.

Compiled Knowledge Objects persist to `data/iko/<TICKER>.json`.

---

## Thesis engine

Every company maintains:

- Current thesis  
- Bull thesis  
- Bear thesis  
- Key assumptions  
- Unknowns  
- Invalidation conditions  

When assertions change → re-evaluate investment thesis.

---

## Decision memory

Stores:

- Previous thesis  
- Assertion changes  
- Evidence changes  
- Research conclusions  

Every decision becomes explainable.

---

## Monitoring engine

Assertions define monitoring triggers. Threshold breach → `SUPPORTED` → `UNDER_REVIEW`.

Delegates status transitions to IKR monitoring evaluation.

---

## Knowledge quality & maturity

Every company receives measured (not assumed) quality:

| Metric | Description |
|--------|-------------|
| `knowledge_coverage` | Claims with non-UNKNOWN state |
| `assertion_coverage` | Required claims addressed |
| `evidence_coverage` | Claims with evidence refs |
| `freshness` | Average evidence freshness |
| `contradiction_count` | Active contradictions |
| `unknown_count` | Unresearched claims |
| `data_quality` | Source trust weighted score |
| `review_status` | healthy / needs_review / stale |

Knowledge maturity assigns institutional grades (A–C) per DNA dimension. See `maturity.py`.

---

## Institutional review

KPE continuously surfaces:

- What do we now know?  
- What changed?  
- What became stronger / weaker / uncertain?  
- What should be monitored?  
- What research should be updated?  

---

## Outputs

- Updated Company DNA (IKO)  
- Updated assertions  
- Updated monitoring rules  
- Updated investment thesis  
- Updated decision memory  
- Knowledge maturity grade  
- Evidence graph delta  
- Research notifications  

---

## Public API

| Method | Mode |
|--------|------|
| `compile_company(ticker)` | Compile |
| `compile_universe(tickers)` | Compile |
| `process_evidence(ticker, items)` | Incremental |
| `normalize_source(raw)` | Both |
| `extract_claims(normalized)` | Incremental |
| `update_company_dna(...)` | Both |
| `evaluate_thesis(iko, changes)` | Both |
| `calculate_maturity(iko)` | Both |
| `calculate_knowledge_kpis(ikos)` | Compile reporting |
| `compute_knowledge_quality(iko)` | Both |
| `institutional_review(iko, changes)` | Both |
| `apply_ikf()` / `apply_kpe()` | Pipeline integration |

---

## Writers

| Writer | Role |
|--------|------|
| `evidence_pipeline` | Primary KPE writer |
| `workflow_completion` | Post-research updates |
| `monitoring_engine` | Status/monitoring only |
| **LLM** | **Never** |

---

## Acceptance tests

| Test | Pass |
|------|------|
| Evidence normalized | ✓ |
| Claims extracted | ✓ |
| Assertions validated | ✓ |
| Company DNA updated (append-only) | ✓ |
| Compile mode merges sources | ✓ |
| Thesis re-evaluated on change | ✓ |
| Decision memory versioned | ✓ |
| Knowledge quality computed | ✓ |
| Knowledge maturity calculated | ✓ |
| Institutional review generated | ✓ |
| Research notifications emitted | ✓ |
| Compiled IKO persisted | ✓ |

---

## Non-goals

KPE does **not**:

- Generate prose for users  
- Perform valuation or forecasting  
- Issue recommendations  
- Store raw documents as knowledge  
- Use LLMs as writers  

---

## What comes next (build only)

1. **NIFTY 50 compilation milestone** — 100% compiled, evidence-linked  
2. **Evidence Graph persistence** — durable evidence → assertion edges  
3. **Decision Memory store** — durable version history  
4. **Wire Ask** — assemble responses from validated Knowledge Objects  
5. **Expand universe** — full Indian market  

*Architecture is frozen. No new specs after this.*
