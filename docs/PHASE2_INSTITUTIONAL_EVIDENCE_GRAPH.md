# AGIB v3.6 Phase 2 Sprint 2.1 — Institutional Evidence Graph (IEG)

## Goal

Retrieve **relationships**, not isolated facts.

```text
Company
  ├── Financials / Segments / Products
  ├── Customers / Suppliers / Competitors
  ├── Management / Shareholding / Risks
  ├── Valuation / Earnings / Guidance
  ├── Macro exposure / Credit / ESG
  └── Historical events
```

Each evidence node stores:

`source · timestamp · confidence · document · paragraph · entity · relationship · expiry · evidence_strength`

## Pipeline insertion

```text
Framework → Playbook → Checklist → Evidence Graph → Reasoning → ICE
```

Soft-wire only. Does **not** redesign KF, IERE internals, or `govern_answer`.

## Package

`intelligence-engine/institutional_evidence_graph/`

Soft-reads:

- IERE ranked evidence (maps evidence types → domains)
- IERI company relationships + transmission paths
- Curated domain stubs + historical event seeds (point-in-time)

## Soft-wires

- Ask Pipeline — after IAP, before planner/governance
- ICE Evidence section — domain coverage + relationship chains
- UiService / Mission Control metadata
- API — `/v1/institutional-evidence-graph/{health,dashboard,company/{ticker},build,history}`

## Replay integrity

When `as_of` is set, nodes with `available_from > as_of` are excluded (no future leakage). Historical event seeds improve Q24 depth without inventing live facts.

## Frozen

KF redesign, reasoning engine, committees, planner — unchanged.

## Exit

Re-run the frozen 25-question CIO exam. Watch Q24 (replay depth) and multi-entity / cross-company questions.
