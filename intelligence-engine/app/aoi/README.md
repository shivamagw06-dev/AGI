# AGI Open Intelligence (AOI) v1.0

Autonomous public knowledge acquisition platform for AGIB.

## Architecture status

**LOCKED — do not redesign:**

- Knowledge Foundation (KF1)
- Knowledge Corpus (KCV1)
- KIP / IRP / RSP / Ask AGI
- Existing APIs and reasoning flow

AOI is a **new subsystem**. It discovers, downloads, parses, validates, versions and soft-publishes public information into KC/KF.

```
Public Sources → Connectors → Scheduler → Download → Parse → Extract
→ Validate → KC/KF (soft) → Ask AGI retrieval
```

## Principles

- Modular, pluggable, configuration-driven connectors
- No cross-connector dependencies
- No hardcoded company-specific connector logic
- Idempotent checksum deduplication
- Append-only version history (never destructive overwrite)
- Fault tolerant soft publish into locked cores

## Package layout

| Module | Role |
|---|---|
| `registry.py` | Canonical company registry + aliases |
| `connector.py` | Connector interface |
| `connectors/` | IR, NSE, BSE, RBI, SEBI, MoF, MOSPI, FRED, IMF, World Bank, PIB + optional stubs |
| `scheduler.py` | Cron/queue/priority scheduling |
| `downloader.py` | Dedup, retries, metadata |
| `parsers.py` | PDF/HTML/XML/JSON/CSV/XLSX/TXT/ZIP detection |
| `validation.py` | Confidence / field validation |
| `versioning.py` | Immutable knowledge versions |
| `diffs.py` | Incremental learning diffs |
| `graph.py` | Relationship graph |
| `quality.py` / `gaps.py` / `digest.py` | Quality, remediation, daily learning |
| `publish.py` | Soft handoff to KIP/KC/KF |
| `pipeline.py` / `service.py` | Acquisition cycle + facade |

## APIs

- `GET /v1/aoi/health`
- `GET /v1/aoi/dashboard`
- `POST /v1/aoi/registry/seed`
- `POST /v1/aoi/run`
- `GET /v1/aoi/companies`
- `GET /v1/aoi/company/{key}`
- `GET /v1/aoi/search`
- `GET /v1/aoi/consult`
- `GET /v1/aoi/connectors`
- `GET /v1/aoi/scheduler`
- `GET /v1/aoi/gaps`
- `GET /v1/aoi/learning`

Node BFF mirrors these under `/api/intelligence/aoi/*`.

## Flags

`AOI`, `AOI_SCHEDULER`, `AOI_PUBLISH`, `AOI_LIVE_FETCH`, plus per-connector toggles (`AOI_NSE`, `AOI_RBI`, …).

Live HTTP fetch is **off by default** (`AOI_LIVE_FETCH=false`) so CI and cold environments remain deterministic. Connectors still produce configuration-driven institutional artifacts offline.

## Extending

1. Implement `SourceConnector`
2. Register via `connectors.factory.register_connector(...)` or add to `_BUILDERS`
3. Add config in `sources_config.CONNECTOR_CONFIGS`
4. Add schedule row in `DEFAULT_SCHEDULE`

No pipeline changes required.

## Roadmap (designed, not implemented)

- **v2:** autonomous source discovery, multi-source reconciliation, trust scoring
- **v3:** AI analyst agents, supply-chain mapping, predictive knowledge updates
