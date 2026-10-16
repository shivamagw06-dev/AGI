# AGIB v3.6 — Phase 2 Sprint 2.2

## Institutional Memory & Analog Intelligence (IMAI)

**Module code:** `IMAI`  
**Package:** `intelligence-engine/institutional_analog_intelligence/`  
**Version:** `institutional-analog-intelligence-v1.0.0`

### Objective

AGIB must ask *"Have we seen this before?"* before reasoning — retrieving validated historical analogues, similar regimes, prior company behaviour, and policy outcomes.

Memory **augments** the Evidence Graph. Memory **never replaces** reasoning.

### Distinct from ILM

| Package | Role |
|---------|------|
| `institutional_memory` (ILM) | Learning / mistakes / forecast calibration — **untouched** |
| `institutional_analog_intelligence` (IMAI) | Historical analogues & regime memory — **this sprint** |

Do not build IMAI as another Knowledge Factory package.

### Soft-wire order

```text
Intent → Evidence → Assembly → Framework → Playbook → Evidence Graph
  → Institutional Memory (IMAI) → Reasoning (frozen) → ICE
```

### Freeze locks

- No new reasoning engine
- No new intelligence packages / KF redesign
- No governance or committee changes
- No planner redesign
- Never fabricate analogues
- Point-in-time: `available_from <= as_of`

### Surfaces

- Ask pipeline packs + stages: `institutional_memory`
- ICE: **Historical Analogues** section + evidence bullets
- Research Office: analogues / lessons only when memories exist
- API: `/v1/institutional-analog-intelligence/*`
- Mission Control board metrics

### Quality gates

FAIL on future leakage, invented analogues, unsupported similarity, incorrect regime, replay mismatch, memory without evidence, impossible confidence.
