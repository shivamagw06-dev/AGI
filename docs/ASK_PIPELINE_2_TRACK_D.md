# AGIB v3.4 Track D — Institutional Communication Engine (ICE)

## Goal

Communicate what Tracks A–C already produced. **Do not invent reasoning.**

```text
InstitutionalAnswer (B/C)
  → Communication Planner
  → Template Selection
  → Evidence Binding
  → Framework Explanation
  → Risk / Confidence / Citations
  → Final Response
```

## Package

`intelligence-engine/institutional_communication/`

Deterministic renderer only. No LLM narrative. No free-form editorial.

## Soft-wires

- Ask Pipeline — after answer binding; returns `communication` + `answer` from ICE
- UiService.search — ICE executive/why **wins** over generic templates
- Research Office — `body.communication` template render (publication logic unchanged)
- Mission Control — ICE board
- API — `/v1/institutional-communication/{health,dashboard,history}`

## Mandatory sections

Executive Summary → Evidence → Framework Used → Analysis → Risks → Confidence → Sources  
(+ Historical Context / Replay Timestamp / Available Evidence / Future Leakage Check for replay)

## Frozen

KF, governance, committees, planner, reasoning — unchanged.

## Exit discipline

Re-run the same 25-question CIO benchmark after merge. Expect material gains in narrative quality, framework visibility, evidence utilisation, and confidence communication.
