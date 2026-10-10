# AGIB v1.0 — General Availability

**Release Status:** GENERAL AVAILABILITY (GA)

**Architecture Status:** Frozen

**Production Foundation:** Complete (PRP-01 · PRP-02 · PRP-03)

**Architecture Conformance:** PASS · 100 (A) — RC-01

---

## Executive Summary

AGIB v1.0 delivers a complete institutional investment intelligence platform with clear architectural boundaries, deterministic reasoning, explainable outputs, production-grade operational foundations, and automated architecture conformance.

```text
Experience
──────────────
Universal Ask AGI
Research Workspace
Publishing

Platform
──────────────
Multi-Portfolio
Security
Performance
Observability

Investment Office
──────────────
Portfolio
Risk
Policy
Committee

Intelligence
──────────────
Decision
Forecast
Observation
Cross-Company

Knowledge
──────────────
Knowledge Graph

Foundation
──────────────
Continuous Gather
Evidence
```

Each layer has a single responsibility.

---

## Core Principles

### Intelligence

* Knowledge Graph is the sole owner of graph state.
* Cross-Company Intelligence reasons over the graph but does not own it.
* Universal Ask AGI orchestrates retrieval but does not generate investment recommendations.
* Publishing composes immutable institutional objects without creating new analysis.
* Multi-Portfolio provides tenancy and workflow without duplicating intelligence.

### Production

* Performance optimizes execution without changing business logic.
* Security determines access without changing intelligence.
* Observability measures execution without influencing behavior.

### Context Separation

Every request carries three independent contexts:

* **Execution Context** — what the request concerns.
* **Security Context** — who is making the request.
* **Observability Context** — how the request is tracked.

---

## Release Statement

**AGIB v1.0 is declared General Availability (GA).**

This release establishes the architectural baseline for all future development.

No changes to core architectural ownership, layer responsibilities, or conformance rules should occur within the v1.0 release line.

---

## Versioning Policy

### v1.0.x

**Permitted**

* Bug fixes
* Performance improvements
* Security patches
* Data coverage expansion
* UI/UX improvements
* Documentation

**Not permitted**

* New architectural layers
* Ownership changes
* Core engine redesigns
* Breaking API changes

### Launch-01 (before v1.1)

Usage validation phase — see `docs/AGI_L_01_LAUNCH.md`.

Do not start v1.1 until Launch Center shows evidence of successful workflows (adoption, SLAs, feedback, conformance).

### v1.1

Built entirely on the v1.0 architecture, justified by Launch-01 evidence:

* Collaboration
* Workflow automation
* Data connector expansion
* AI-assisted analyst productivity (not recommendations)
* International market coverage
* External integrations

### v2.0

Reserved for intentional architectural evolution requiring a new architecture review and updated conformance rules.

---

## Success Metrics (post-GA)

Track product and operations, not expansion count:

* Daily / weekly active analysts
* Median Ask AGI response time
* Workspace engagement
* Publication generation success rate
* Data freshness SLAs
* Architecture conformance rate (target: 100%)
* System availability
* Production incident rate
* Research output quality
* Customer retention and satisfaction

---

## Related

* `docs/AGIB_V1_ARCHITECTURE_FREEZE.md`
* `docs/AGI_RC_01_ARCHITECTURE_CONFORMANCE.md`
* `docs/AGI_PRP_PROGRAMME.md`
* `docs/AGI_L_01_LAUNCH.md`
* `docs/AGI_PAT_01_PRODUCTION_ACCEPTANCE.md` — break AGIB before onboarding users
* `docs/AGI_IB_01_INSTITUTIONAL_BENCHMARK.md` — competitive intelligence grade (≠ software acceptance)
* CI: `.github/workflows/architecture-conformance.yml`
