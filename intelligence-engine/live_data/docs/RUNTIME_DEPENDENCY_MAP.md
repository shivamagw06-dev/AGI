# LIDI — Runtime Dependency Map

## Principle

```
Official Source → Collector → Validator → Derived Producer → Knowledge Object → Evidence Pack → Platform
```

Never connect a source directly to Reasoning.
Never silent fixture fallback in production.

## Track-1 collectors (ordered)

1. `nse_bhavcopy` — NSE Bhavcopy
2. `nse_announcements` — NSE Corporate Announcements
3. `bse_corporate_actions` — BSE Corporate Actions
4. `rbi_dbie` — RBI DBIE
5. `company_ir` — Company Investor Relations

## Soft-wires

| Surface | Integration |
|---|---|
| Institutional Scheduler | `handle_historical` soft-calls `live_data.run_morning_live_ingestion` before KF daily |
| Knowledge Factory | LIDI writes objects/packs under `data/live_data/`; optional `lidi.validated.publish` event |
| Research Office | Soft signal / disk packs after publish — knowledge only |
| Mission Control | Soft board `live_institutional_data` |
| Reasoning / Governance | **Untouched** |

## Fallback

Live unavailable → latest **validated LIDI snapshot** → mark freshness / transparent insufficiency.

Fixtures / recorded samples only when explicitly requested (`allow_recorded_sample=True` or `LIDI_ALLOW_RECORDED_SAMPLE` outside production).

## APIs

- `GET /v1/live-data/status`
- `GET /v1/live-data/sources`
- `GET /v1/live-data/freshness`
- `GET /v1/live-data/collectors`
- `GET /v1/live-data/validation`
- `GET /v1/live-data/fallback`
- `GET /v1/live-data/dashboard`
- `POST /v1/live-data/run`
