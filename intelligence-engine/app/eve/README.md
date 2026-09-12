# AGI Evidence & Verification Engine (EVE) v1.0

Institutional fact verification, provenance, and trust layer.

## Position

```
AOI → Structured Facts → EVE → KCV → KF → KIP → Ask AGI
```

## Architecture status

**LOCKED — do not redesign:** KF1, KCV1, AOI, KIP, IRP, RSP, Ask AGI.

EVE integrates only through soft extension points:

- Optional `eve=` on AOI publish
- Soft `bind_eve()` on AOI service
- Soft Ask AGI `evidence_verification` consult

## Owns

- Source registry + configurable reliability
- Immutable evidence objects + provenance
- Fact normalisation
- Multi-source validation
- Conflict detection (preserve both sides)
- Confidence engine
- Timeline events
- Fact versioning
- Relationship validation
- Knowledge health
- Daily verification jobs
- Audit trail

## APIs

`/v1/eve/health|dashboard|evidence|company/{id}|conflicts|timeline|trust|source|verification|search|consult|audit`

Node BFF: `/api/intelligence/eve/*`

Admin: `/admin/evidence`

## Flags

`EVE`, `EVE_AUTO_VERIFY`, `EVE_GATE_PUBLISH`, `EVE_CONFLICTS`, `EVE_TIMELINE`, `EVE_DAILY_JOBS`

Reliability and normalisation tables live in `config.py` (not hardcoded in logic).
