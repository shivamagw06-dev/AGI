# Company Intelligence Dossier (CID) v1.0

**Not an engine. Not a knowledge library.** Permanent institutional memory for every tracked company.

Built on LEO: every verified evidence object updates the living dossier. Ask AGI / CAE start company analysis from the dossier — never rebuild from raw APIs.

## Flow

```
LEO evidence → EVE verify → CID ingest → timelines/metrics/KPIs
Ask AGI / CAE → load CID first → Academy → SIF → IRP → Answer
```

## Flag

`CID=true` (default)

## APIs

- `GET /v1/company-dossier/{ticker}`
- `GET /v1/company-dossier/{ticker}/timeline`
- `GET /v1/company-dossier/{ticker}/coverage`
- `GET /v1/company-dossier/{ticker}/valuation`
- `GET /v1/company-dossier/{ticker}/risk`
- `GET /v1/company-dossier/{ticker}/forecast`
- `GET /v1/company-dossier/{ticker}/documents`
- `GET /v1/company-dossier` (dashboard)
- `GET /v1/company-dossier/quality-gates`

Admin: `/admin/company-dossiers`
