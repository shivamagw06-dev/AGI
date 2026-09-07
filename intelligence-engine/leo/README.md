# Live Evidence Orchestrator (LEO) v1.0

**Not a reasoning engine.** Additive production capability that gathers, verifies, ranks and packages live external evidence **before** Ask AGI / CAE / Academy / SIF / IRP reason.

## Flow

```
Question
  → Entity + Intent detection
  → Evidence Plan
  → Dynamic source selection
  → Vendor / AOI / Agib fetches
  → Canonical Evidence Objects
  → EVE verification (soft)
  → Company dossier update
  → Quality gate
  → Package into CAE / Ask AGI / IRP
  → Finance Academy + SIF + IRP answer
```

## Flag

`LEO=true` (default). Soft-fails when disabled.

## Soft attach points

- `UiService.search` — runs LEO first; feeds `sif_evidence_supplied`; exposes `SearchView.live_evidence`
- `CaeAssembler._soft_fields` — `live_evidence`
- `IrpPipeline.run` — injects LEO objects into ranked evidence; `IrpPackage.live_evidence`

## API

- `GET /v1/leo/health`
- `GET /v1/leo/dashboard`
- `POST /v1/leo/package?query=&ticker=`
- `GET /v1/leo/quality-gates`
- `GET /v1/leo/dossier/{ticker}`

Admin: `/admin/live-evidence`
