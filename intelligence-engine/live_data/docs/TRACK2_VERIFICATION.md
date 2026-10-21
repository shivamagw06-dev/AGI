# LIDI Track 2 — Live Collector Activation & Production Verification

## Scope

Activate, verify, and certify Track-1 collectors. **No new architecture.** Frozen packages untouched.

## Certification levels

`NOT_IMPLEMENTED → DEVELOPMENT → TESTING → STAGING → PRODUCTION_READY → CERTIFIED`

**CERTIFIED** requires **7 consecutive successful LIVE daily runs** with no fixture fallback, no replay corruption, no provenance/validation failures.

## Surfaces

| API | Purpose |
|---|---|
| `POST /v1/live-data/verification/run` | Full verification pass |
| `GET /v1/live-data/verification/dashboard` | Collector Health Dashboard |
| `GET /v1/live-data/verification/certification` | Certification state |
| `GET /v1/live-data/verification/telemetry` | Collector telemetry |
| `GET /v1/live-data/verification/probes` | Live endpoint probes |
| `POST /v1/live-data/verification/report/generate` | Write certification report |

## Report

`docs/LIVE_DATA_CERTIFICATION_REPORT.md`
