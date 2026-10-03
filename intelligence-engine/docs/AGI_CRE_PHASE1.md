# AGI Causal Research Engine — Phase 1

Phase 1 establishes immutable causal contracts and governance. It does not add another graph, event store, thesis engine or knowledge registry.

Implemented objects:

- `EvidenceReference`
- `CausalRelationship`
- `CounterEffect`
- `ContradictionGroup`
- `FinancialImpact`

The contracts distinguish facts, observations, calculations, scenarios, forecasts, causal interpretations, hypotheses, theses and opinions. Validation enforces provenance, evidence status, point-in-time availability, validity windows, confidence ranges and scenario/AFE trace requirements.

Existing CIG and Economic Relationship Intelligence records enter CRE through read adapters. No model-facing graph mutation is provided. Models may create `PROPOSED` candidates but cannot transition knowledge to `VALIDATED` or `TRUSTED`.

Deferred to later phases: durable database tables, graph retrieval, event extraction, AFE execution, scenario/valuation execution, thesis updates, Ask AGI tools and outcome learning.
