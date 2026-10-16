# AGIB Phase 3 — Sprint 3.3 Framework Optimisation

Optimise the **selector**, not a new framework engine.

## Changes

- `framework_selection/mappings/cues.py` — cue overlays
- Sector composition enrichment (banks / NBFC / IT / airlines)
- Selector applies cues + enrichment after intent overlays
- Patch Intelligence (`patch_intelligence/`) — human-in-the-loop briefs only

## Loop

RCI cluster → Patch brief → Human implements → IEL regression → Merge
