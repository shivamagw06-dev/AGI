# Finance Academy Production Integration (FAPI) v1.0

FAPI is **not a new engine**.

It is an additive integration capability that makes the existing Finance Academy an active participant in production reasoning.

## Flow

```
User Question
  → CAE (packages Academy context)
  → Finance Academy Retrieval (concepts, causal, mental, formulas, graph)
  → IIE / VE / EVE / FLE soft consumers
  → IRP (reasons with Academy provenance)
  → Ask AGI (finance answers cite Academy influence)
```

## Flags

| Env | Default | Meaning |
|---|---|---|
| `ACADEMY` | true | Library enabled |
| `ACADEMY_PRODUCTION` | true | FAPI production wiring enabled |

When `ACADEMY_PRODUCTION=false`, soft attachments no-op and VE keeps hardcoded defaults (A/B OFF path).

## Soft attach points (locked engines unchanged in design)

- `app/cae/assembler.py` / `assemble_for_ask_agi`
- `app/ui/service.py` `search`
- `app/irp/pipeline.py` `run`
- `app/ve/inputs.py` `gather_inputs` + `VeService.consult`
- `app/eve/service.py` `consult`
- `app/iie/service.py` `consult`
- `app/fle/service.py` `consult`
- `app/kf/service.py` `search`
- `app/kc/service.py` `consult`

## Admin / API

- `GET /v1/academy/production` — usage dashboard
- `GET /v1/academy/production/ab` — A/B probe
- `GET /v1/academy/production/quality-gates` — completion gates
- `POST /v1/academy/production/package` — retrieve package for a query
- Admin UI: `/admin/academy` → Production usage (FAPI)

## Validation

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m pytest tests/test_finance_academy_fapi_v1.py -q
PYTHONPATH=. python3 -m academy.audit.harness
```
