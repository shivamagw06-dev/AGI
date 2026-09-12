# RC-01 — Architecture Conformance & Release Candidate

Quality gate for **AGIB v1.0**. Not a feature.

## Mission

Prove that every future change preserves AGIB v1.0's architectural principles.

## Milestone

| Gate | Status |
|------|--------|
| AGIB v1.0 Architecture | Complete |
| Production Foundation (PRP-01/02/03) | Complete |
| RC-01 Conformance | This workstream |
| AGIB v1.0 GA | After RC-01 passes consistently |

## Guiding principle

> This is a quality gate. It protects the architecture — it does not expand it.

## Package

`intelligence-engine/institutional_architecture/`

## Checks

### Intelligence ownership

- Knowledge Graph is the only graph owner (KG-01)
- CCI owns relationships, not graph state
- UAG owns orchestration, not recommendations
- PUB owns composition, not reasoning
- MPC owns tenancy, not intelligence
- RW is presentation-only

### Production isolation

- Security never modifies intelligence
- Observability never changes execution
- Performance never owns business logic
- Architecture freeze flags hold

### Contexts

Every platform request may carry:

1. `InstitutionalExecutionContext` — what
2. `InstitutionalSecurityContext` — who
3. `InstitutionalObservabilityContext` — how

### Dependency rules

Forbidden imports such as Decision → Security or Knowledge Graph → Workspace fail the gate.

### Lineage

```text
Evidence → Decision → Risk → Policy → Portfolio Decision → Committee → Publication
```

Publication path: Publication → Manifest → Evidence.

### UAG

Ask must route through registered engines and must not generate recommendations.

## CLI / CI

```bash
cd intelligence-engine
PYTHONPATH=. python -m institutional_architecture
```

Exit code `1` when violations exist (`AGI_RC_01_FAIL_ON_VIOLATION=true`).

GitHub Actions: `.github/workflows/architecture-conformance.yml`

## Mission Control — Architecture Center

Soft-slice key: `institutional_architecture`

- Architecture score / grade
- Invariants / violations
- Layer dependencies / import graph
- Context propagation
- Lineage health
- Release-candidate ready

## APIs

- `GET /v1/architecture/health`
- `GET|POST /v1/architecture/conformance`
- `GET /v1/architecture/report`
- `GET /v1/architecture/violations`

## After RC-01

**AGIB v1.0 General Availability (GA) is declared** — see `docs/AGIB_V1_0_GA.md`.

RC-01 remains the continuous CI gate for the v1.0 release line.

AGIB v1.1 product enhancements (collaboration, automation, data expansion, mobile/executive, AI productivity) build on this stable foundation — they do not change it.
