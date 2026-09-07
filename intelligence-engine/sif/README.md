# Sector Intelligence Framework (SIF) v1.0

SIF is **not a new engine** and **not a curriculum**.

It is an additive institutional analysis framework that teaches AGI *when, where, and how* to apply Finance Academy concepts by sector.

## Flow

```
Question
  → Company / Sector Detection
  → Sector Framework (KPIs, valuation, mental models)
  → Company Evidence Gate
  → Finance Academy (sector-boosted)
  → IIE / VE / IRP / Ask AGI
```

## Flags

| Env | Default | Meaning |
|---|---|---|
| `SIF` | true | Enable sector frameworks |
| `ACADEMY_PRODUCTION` | true | Required for production soft wiring |

## Soft attach points

- `academy/fapi/production.py` — sector-aware Academy ranking
- `app/ui/service.py` — Ask AGI provenance + evidence gate
- `app/irp/pipeline.py` — sector-enriched reasoning
- `app/ve/service.py` — preferred valuation methodology
- `app/iie/service.py` — sector IIE focus

## API

- `GET /v1/sif/health`
- `GET /v1/sif/dashboard`
- `GET /v1/sif/frameworks`
- `GET /v1/sif/frameworks/{sector_id}`
- `POST /v1/sif/analyse?query=...&ticker=...`
- `GET /v1/sif/quality-gates`

## Validation

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest tests/test_sif_v1.py -q
```
