# Phase 6.0 — Universal Knowledge Orchestration (UKO)

One planner. One provider registry. One evidence graph.
Every Ask question is planned once, gathers evidence once, and composes one
institutional answer. Routing never decides which knowledge AGI can see.

## Architecture

```
User Question
    ↓
Entity Resolution          (entity_intelligence — authoritative bind / refusal)
    ↓
Universal Knowledge Planner  (universal_knowledge/planner.py)
    ↓
Provider Registry            (KUL implementations + UKO capability matrix)
    ↓
Evidence Collection          (provider.consult for every selected id)
    ↓
Evidence Graph               (role-ordered: identity → industry → business →
                              financials → valuation → investment → research)
    ↓
Fusion / Composer            (knowledge_unification.fusion — institutional prose)
    ↓
Institutional Answer
```

Both Ask paths call the same gather:

| Path | Entry | UKO call |
|------|-------|----------|
| KUL short-circuit | `knowledge_unification.production.answer_for_ask` | `universal_knowledge.production.for_ask` |
| Full desk | `ask_pipeline.knowledge.retrieve_knowledge` | `universal_knowledge.production.for_ask_pipeline` |

Evidence assembly then surfaces the UKO graph as a first-class pack
(`ask_pipeline/evidence.py` → `packs["universal_knowledge"]`).

## Provider registry

19 providers, registered once in `knowledge_unification/providers/__init__.py`
and described in `universal_knowledge/registry.py:CAPABILITIES`:

| id | role | authority |
|----|------|-----------|
| capiq_ikt | identity | institutional |
| industry_intelligence | industry | institutional |
| business_intelligence | business | institutional |
| financial_statement_warehouse | financials | warehouse |
| valuation_terminal | valuation | market |
| valuation_consensus | valuation | consensus |
| hedge_fund_screens | investment | institutional |
| investment_intelligence | investment | institutional |
| portfolio_intelligence | portfolio | institutional |
| research_intelligence | research | institutional |
| company_memory / ikl / knowledge_factory / cgl | memory | institutional |
| financial_concepts / foundations / statement_intelligence / academy | pedagogy | pedagogical |
| legacy_kip | research | institutional |

Future engines (macro, news, ESG, credit, private markets) become available
to Ask by registering a provider — no routing work required.

## Financial Statement Warehouse

`financial_statement_warehouse` is a mandatory UKO provider. It reads the FSE
warehouse when parsed facts exist, and falls back to CapIQ IKT LTM figures
(revenue, EBITDA, …) so Ask always has numerical financial evidence while the
warehouse is filling. Valuation questions expect this provider; silence is a
coverage failure, not a silent skip.

## Coverage

Every gather returns:

```
providers_selected
providers_expected
providers_used
providers_missing
coverage_pct
average_confidence
attributions
```

Missing expected providers are flagged — UKO never silently continues.

## Acceptance

```
cd intelligence-engine
python3 scripts/universal_coverage_acceptance_v1.py
```

Target: 100% pass, route independence true, zero missing core providers.

Verified locally (uko-6.0):

- 7/7 cases passed
- route independence: true
- Axis Bank / TCS valuation → valuation_terminal + consensus + industry + warehouse
- Infosys consensus → valuation_consensus leads
- Ashoka screen → hedge_fund_screens + valuation_terminal
- Bank valuation pedagogy → industry_intelligence + financial_concepts

## API

```
GET  /v1/universal-knowledge/health
GET  /v1/universal-knowledge/registry
POST /v1/universal-knowledge/orchestrate   { "question": "…", "ticker": "…" }
```

Proxied at `/api/intelligence/universal-knowledge/*`.

## What this does not yet include

- A Mission Control provider-health UI page (API is ready; page pending)
- Macro / news / ESG / options / credit providers (registry slots reserved by design)
- Populated FSE warehouse rows for every ticker (provider is wired; CapIQ LTM
  stands in until filings are loaded)
- Full regression of every pre-existing acceptance suite against UKO (Core
  Platform, Founder Golden, etc.) — run those before merge to main
