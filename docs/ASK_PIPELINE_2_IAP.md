# AGIB v3.5 — Institutional Analytical Playbooks (IAP)

## Goal

Guide reasoning with institutional checklists and multi-step analytical procedures.

**Not** another intelligence package. **Not** a replacement for reasoning.

```text
Framework Selection
      ↓
Institutional Playbook
      ↓
Analytical Checklist
      ↓
Reasoning (guided)
      ↓
Communication
```

## Package

`intelligence-engine/institutional_playbooks/`

Registry layout:

```text
registry/
  company/          (12)
  valuation/        (8)
  industry/         (8)
  macro/            (8)
  government/       (5)
  documents/        (5)
  investment_committee/ (4)
  accounting/       (helpers)
  replay/           (helpers)
  quality/          (helpers)
```

≈ **50** V1 playbooks.

## Every playbook contains

- Question types + cues
- Aligned frameworks
- Analytical checklist
- Ordered procedure
- Evidence required
- Knowledge objects
- Confidence rules
- Common mistakes
- Output structure

## Soft-wires

- Ask Pipeline — after IFSE, before planner/governance; packs `playbook_selection`
- ICE — renders Analytical Checklist + injects procedure into Analysis
- UiService.search — surfaces `playbook_selection` / `playbook_visible`
- Mission Control — IAP board
- API — `/v1/institutional-playbooks/{health,dashboard,registry,playbook/{id},select,history}`

## Frozen

KF, governance internals, committees, planner redesign, reasoning engine redesign — unchanged.

IAP **guides** reasoning via packs + communication; it does not rewrite `govern_answer`.

## Exit discipline

Re-run the same 25-question CIO exam. Watch Q17–Q23 (checklists, multi-step procedures, document review, IC thought process). Target band after playbooks: **7.8–8.2**.
