# Phase 3.0 — Business Intelligence Foundation

## Objective

Teach AGI **why** businesses succeed or fail — not only what financial
statements show. Deterministic, institutional, explainable.

## Package

`intelligence-engine/business_intelligence/foundation/`

Extends the existing FIRE-03 `business_intelligence/` package (disclosure
extraction). Phase 3.0 is the **reasoning layer** on top of CapIQ/IKT
evidence + industry templates + financial_concepts vocabulary.

| Module | Engine |
|---|---|
| Business Model | `engines.analyse_business_model` |
| Value Drivers | industry templates (NIM/CASA, NRR/CAC, …) |
| Unit Economics | Revenue→GP→CM→OP→FCF mapped per industry |
| Moat | scored dimensions (brand, network, scale, …) |
| Industry / Porter | structured five-forces per industry |
| Growth | growth-mode matrix |
| Management | evidence-gated (Unknown if no filings) |
| Risks | industry-prior risk scores |
| Lifecycle | stage classification |
| Comparison | business axes, not ratios alone |
| Knowledge Graph | company↔industry↔competitors↔products |

## Ask integration

**Phase 3.0.5** wires Ask exclusively through KUL provider
`business_intelligence` (see `PHASE3_05_NOTES.md`).

`ask_wired: true` · `ask_wired_via: knowledge_unification.providers.business_intelligence`

Do not add a parallel short-circuit in `app/ui/service.py` — KUL is the path.

## API

- `GET /business-intelligence/foundation/health`
- `GET /business-intelligence/foundation/dashboard`
- `POST /business-intelligence/foundation/analyse` `{question, ticker?, industry?}`
- `GET /business-intelligence/foundation/industry/{key}`
- `GET /business-intelligence/foundation/company/{ticker}`
- `GET /business-intelligence/foundation/graph/{ticker}`
- `POST /business-intelligence/foundation/compare` `{question}`

## Acceptance

```bash
cd intelligence-engine
python3 -m ask_product_test.run_bi_acceptance_v1
```

100 questions · gate ≥95% · writes `/workspace/artifacts/bi_acceptance_v1.json`

## Reuse (do not duplicate)

- CapIQ IKT `business_model` / `company_master` tables
- `financial_concepts` moat/unit-econ definitions (vocabulary)
- `knowledge_factory.industry_intelligence` playbooks (soft)
- FIRE-03 extractors remain the disclosure path

## Next (after acceptance green)

1. Wire Ask short-circuit for business questions via KUL provider
2. Founder Evaluation — 50 live business questions
3. Deeper management scoring from filings / kip_v2
