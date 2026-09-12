# Sprint 6.1 — Knowledge Acquisition Platform (KAIP)

## Goal

Build a **standalone** always-on Knowledge Acquisition Platform that continuously ingests institutional data, converts it into AGI’s canonical knowledge model, and publishes Knowledge Objects to the Intelligence Engine.

KAIP does **not** perform reasoning.

## Contract

Authoritative contract: [`knowledge-platform/docs/KAIP_PLATFORM_CONTRACT.md`](../knowledge-platform/docs/KAIP_PLATFORM_CONTRACT.md)

## Service location

```text
knowledge-platform/
```

Separate from `intelligence-engine/`.

## What shipped

- Platform contract (stable envelopes, canonical fields, five KO types, internal APIs)
- Acquisition scheduler (finance-agnostic job runner)
- Collectors: Yahoo, NSE announcements, NSE bhavcopy, BSE corporate actions, Company IR
- Append-only `raw_events`
- Validation gates
- Canonical normalizer (provider → AGI language)
- Entity resolution (Company / Sector / Industry / Index / Peers)
- Knowledge Object builder (5 types only)
- Relationship builder
- Change detection → Learning Events (material deltas only)
- Publisher (Knowledge Objects only — never raw provider JSON)
- Internal retrieval APIs
- Thin IE read client: `intelligence-engine/app/kaip_client/`

## Success path

```text
Yahoo updates Infosys
 → YahooCollector
 → raw_events
 → validate / normalize / resolve
 → CompanyProfile (+ MarketSnapshot / FinancialStatement)
 → LearningEvent if material (e.g. revenue growth 18% → 28%)
 → publish
 → GET /v1/knowledge/company/INFY
```

Verified by `knowledge-platform/tests/test_infosys_success_path.py`.

## Explicit non-goals (deferred)

IEW / IHG / IHE integration · reasoning · LLM summarisation · embeddings · vector search · Evidence Graph enrichment · portfolio updates · Monitoring Office updates
