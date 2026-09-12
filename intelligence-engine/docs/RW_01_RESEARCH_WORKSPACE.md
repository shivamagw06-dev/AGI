# RW-01 — Institutional Research Workspace (engine notes)

Engine package: `institutional_workspace`.

## Façades

`production.py`:

- `health()` / `soft_slice_mission_control()`
- `get_company_workspace` / `get_portfolio_workspace` / `get_committee_workspace`
- `get_timeline` / `get_object` / `search` / `add_analyst_note`

## Soft dependencies

RW-01 soft-calls (never hard-fails):

- Company decision (IDS)
- PRE-01 portfolio risk
- PCE-01 policy
- CIO-01 portfolio decision
- ICE-01 committee

Missing upstream objects appear as diagnostics (`missing_links`), not crashes.

## Ask integration

UAG-01 `ask()` returns a soft `workspace` block:

```json
{
  "focus": "timeline",
  "href": "/agi/companies/AXISBANK?tab=timeline&rw=1",
  "lineage_hint": ["Decision", "Timeline", "Observation", "Evidence"],
  "engine": "RW-01"
}
```

## Tests

`tests/test_rw_01_research_workspace.py`
