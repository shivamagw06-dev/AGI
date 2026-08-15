# AGI Autonomous Intelligence Architecture

## Status

AGI already operates as a multi-layer institutional research platform. This
upgrade extends existing engines; it does not create a parallel stack.

## Architecture map

```text
Client question
  -> Ask gateway and trace                  [EXISTING]
  -> intent + entity + temporal resolution  [EXISTING]
  -> knowledge-gap and research planning    [EXISTING, EXTEND]
  -> governed read tools                    [EXISTING, STANDARDIZE]
       -> KIP/research/company dossiers
       -> financial warehouse/market data
       -> industry intelligence/causal graph
       -> theses, versions and outcomes
       -> current-world research providers
  -> evidence assembly + authority gates    [EXISTING, EXTEND]
  -> deterministic financial calculation    [EXISTING]
  -> institutional reasoning                [EXISTING]
  -> provider-independent synthesis          [MODIFIED]
  -> critic + citation/numeric validation    [EXISTING, EXTEND]
  -> client answer + internal trace          [EXISTING]
  -> proposed learning candidate             [NEW]
  -> validated -> trusted promotion          [NEW, HUMAN GATE PENDING]
  -> outcome monitoring and calibration      [EXISTING, CONNECT]
```

## Existing systems to reuse

- Ask pipeline: intent resolution, entities, temporal classification, policy,
  planner, DAG, evidence assembly, gates, answer assembly and recording.
- Knowledge: KIP, company dossiers, company memory/workspaces, research registry,
  semantic research, provenance and evidence packs.
- Intelligence: industry drivers, causal graph and propagation, scenario and
  counterfactual engines, thesis engines and versioned company views.
- Financial layer: warehouse financial history, financial router, deterministic
  factors, forecasts, validation, market and macro providers.
- Governance: evidence quality, citations, unsupported-number rejection,
  recommendation policy, traces, acceptance suites and production gates.
- Learning: durable jobs, evidence records, candidate lifecycle, theses,
  monitors, learning examples and outcome records.

## Implemented in this slice

- `ReasoningProvider` contract with normalized structured generation.
- OpenAI, Anthropic, Google and local/open-weight provider adapters.
- Configuration through `ASK_MODEL_PROVIDER`, `MODEL_PROVIDER`, or
  `AGI_REASONING_PROVIDER` rather than provider-specific business logic.
- Ask AGI grounded synthesis moved behind the provider contract.
- Continuous intelligence learning moved behind the provider contract.
- Proposed/validated/trusted/quarantined candidate lifecycle remains database
  owned; model output cannot self-promote to trusted knowledge.

## Material gaps

1. Standardize the existing tool modules into one versioned read/write registry.
2. Add provider-independent web search and document retrieval adapters with
   authority tiers, licenses, budgets and original-source verification.
3. Execute iterative gap-driven research; the current planner records a plan but
   Ask's default DAG remains mostly deterministic and sequential.
4. Add contradiction objects and confidence updates across new versus historical
   evidence rather than relying only on per-answer critique.
5. Add human/admin promotion and rejection workflow for validated candidates.
6. Connect trusted learning candidates to KIP, industry DNA, causal graphs and
   thesis versions through explicit promotion transactions.
7. Connect thesis/forecast outcome records to confidence calibration and reviewed
   learning examples.
8. Consolidate remaining direct model calls in dossiers, editorial, macro and
   publishing paths behind the same provider interface.

## Trust policy

```text
PROPOSED -> automated evidence/critic checks -> VALIDATED
VALIDATED -> repeated/primary/deterministic/human support -> TRUSTED
Any stage -> insufficient support -> QUARANTINED
Any stage -> disproven/erroneous -> REJECTED or SUPERSEDED
```

Only `TRUSTED` objects may be used as durable institutional knowledge. Proposed,
validated and quarantined objects remain reviewable evidence candidates.

## Rollback

- Set `ASK_LLM_ENABLED=0` to use the deterministic Ask answer path.
- Set `AGI_INTELLIGENCE_LEARNING_ENABLED=false` to stop new learning jobs.
- Set the provider variables back to `openai` without schema changes.
- Candidate and audit records are append-oriented; rollback code must not delete
  source documents, evidence, prior thesis versions or learning receipts.

## Next acceptance gate

Run the five questions in the autonomous-intelligence specification and verify:

- current questions trigger freshness requirements;
- only attributable evidence is used;
- causal and financial transmission is present;
- contradictory evidence and invalidation conditions are explicit;
- unsupported numbers are rejected;
- provider switching changes no answer schema or governance behavior.
