# AGI Causal Research Engine: Phases 2-10

## Operating boundary

CRE reuses AGI's existing CIG, corporate-event, AFE, valuation, thesis, tool,
provenance, and learning systems. It does not introduce a second graph or a
second thesis registry. Outputs are research context and governed proposals;
execution remains blocked.

## Implemented phases

| Phase | Capability | Authority |
| --- | --- | --- |
| 2 | Bounded relevant-subgraph retrieval from the existing CIG | Read |
| 3 | PIT-safe event normalization and event-to-relationship matching | Propose |
| 4 | Deterministic financial transmission through AFE | Calculate |
| 5 | Explicit bear/base/bull scenario assembly | Propose |
| 6 | Thesis update proposals with invalidation and monitoring fields | Propose |
| 7 | Contradiction detection, validity windows, temporal slicing | Read |
| 8 | Document-to-candidate learning and quarantine | Propose |
| 9 | Governed `GET_CAUSAL_RESEARCH` Ask AGI tool | Read |
| 10 | Evidence-required outcome scoring | Propose |

## Governance

- Models cannot promote their own candidates.
- Learning and outcome records begin as `PROPOSED`.
- Future-dated evidence is rejected from point-in-time analysis.
- Unsupported AFE calculations are quarantined.
- Scenario probabilities must sum to one and are labelled `SCENARIO`.
- Thesis integration produces a proposal; it does not mutate ITCE.
- Ask AGI receives a bounded evidence context, not an execution instruction.

## Deliberate limitations

- CRE does not claim historical alpha or investment validation.
- Graph coverage remains bounded by existing CIG/IERI coverage.
- Event candidate matching is deterministic and conservative.
- Authorized review and persistent storage remain owned by existing AGI
  governance and knowledge-registry infrastructure.
