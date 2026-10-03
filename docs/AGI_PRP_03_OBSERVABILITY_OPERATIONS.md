# PRP-03 — Observability & Operations

Production Readiness Programme workstream 3. Completes the production foundation: fast (PRP-01), secure (PRP-02), operable (PRP-03).

## Guiding principle

> **Observability explains how the platform behaves. It never changes platform behavior.**

## Status

Architecture remains **frozen at AGIB v1.0**. Observability wraps the platform — it never enters the intelligence layer and never alters execution.

## Three contexts

Every platform request can carry:

| Context | Answers |
|---------|---------|
| `InstitutionalExecutionContext` | What the request is about |
| `InstitutionalSecurityContext` | Who is making the request |
| `InstitutionalObservabilityContext` | How the request is tracked |

## Package

`intelligence-engine/institutional_observability/`

## Capabilities

| Area | Implementation |
|------|----------------|
| Distributed tracing | `InstitutionalTrace` + spans; correlation ID from PRP-02 |
| Metrics | Request count, P50/P95/P99, cache, queue, jobs, errors, auth failures |
| Structured logs | Required fields including correlation_id / trace_id / tenant / portfolio |
| Health | Liveness, readiness, per-service probes |
| Alerting | Consumes metrics only — never business objects |
| Dependency monitor | Service graph for outage diagnosis |
| Service map | Topology for Mission Control |

## Mission Control — Operations Center

Soft-slice key: `institutional_observability`

- Live request rate · Active traces · P95/P99
- Error rate · Queue / cache health · Worker utilization
- Dependency status · Alert timeline · Service topology

## APIs

- `GET /v1/ops/health`
- `GET /v1/ops/metrics`
- `GET /v1/ops/traces/{id}`
- `GET /v1/ops/service-map`
- `GET /v1/ops/alerts`
- `GET /v1/ops/dependencies`
- `GET /v1/ops/logs`
- `GET /v1/observability/health`

## Soft integration

UAG / RW / PUB call observability middleware **around** execution. Results are never rewritten for business meaning — only observability envelopes are attached.

## Flags

| Env | Default | Meaning |
|-----|---------|---------|
| `AGI_PRP_03_ENABLED` | true | Master switch |
| `AGI_PRP_03_MIDDLEWARE` | true | Soft request wrapping |
| `AGI_PRP_03_ALERTS` | true | Alert evaluation |

## Invariants

- Every request is traceable end-to-end
- Correlation IDs from PRP-02 flow through all spans
- Platform metrics available in real time
- Observability completely separate from intelligence logic
- No domain engine depends on tracing or metrics
- No new intelligence engines
