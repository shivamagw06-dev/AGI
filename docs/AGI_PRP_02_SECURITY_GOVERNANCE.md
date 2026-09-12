# PRP-02 — Security & Governance

Production Readiness Programme workstream 2. Enterprise controls for AGIB without modifying intelligence engines.

## Guiding principle

> **Security decides who can perform an operation. Intelligence decides what the operation means.**

## Status

Architecture remains **frozen at AGIB v1.0**. PRP-02 wraps the platform — it never enters the intelligence layer.

## Architecture

```text
Client → Authentication → Security Gateway → Authorization + Audit
                                              ↓
                                    AGIB Orchestration
                                    (UAG · RW · PUB · MPC)
                                              ↓
                                    Intelligence Layer (SoR)
```

## Package

`intelligence-engine/institutional_security/`

## Core objects

### InstitutionalSecurityContext

Complements `InstitutionalExecutionContext`:

- `user_id`, `tenant_id`, `role`, `permissions`
- `authentication_method`, `api_key_id`, `session_id`
- `correlation_id`, `diagnostics`

### InstitutionalAuditEvent

Immutable, append-only. References resource IDs — does not duplicate business objects.

## Capabilities

| Area | Support |
|------|---------|
| Authentication | Password, SSO, OAuth2, OIDC, API keys, service accounts |
| Authorization | RBAC + capability permissions |
| Roles | Administrator, CIO, PM, Research Analyst, Compliance, Read Only, Service Account |
| Tenant isolation | Users / clients / portfolios / publications / workspaces; intelligence global |
| API keys | User / service / read-only; scoped; expire; rotate; revoke |
| Sessions | Login, logout, refresh, expiration, impersonation field, concurrent |
| Encryption | Secret hashing, at-rest seal for tokens/session material |
| Correlation ID | Flows across security → orchestration → audit |

## Mission Control — Security Center

Soft-slice key: `institutional_security`

- Active sessions · Login failures · API key usage
- Permission changes · Audit volume · Tenant count
- Revoked tokens · Authentication latency

## APIs

- `POST /v1/auth/login|logout|refresh`
- `GET/POST /v1/security/context`
- `GET/POST /v1/security/audit`
- `POST /v1/security/api-keys` · `DELETE /v1/security/api-keys/{id}`
- `GET /v1/security/roles|permissions|tenants`

## Soft integration

Platform façades (UAG / RW / PUB) call the Security Gateway **before** orchestration when credentials are present or `AGI_PRP_02_ENFORCE=true`. Domain engines remain unaware of users and roles.

## Flags

| Env | Default | Meaning |
|-----|---------|---------|
| `AGI_PRP_02_ENABLED` | true | Master switch |
| `AGI_PRP_02_ENFORCE` | false | Require auth on all gated ops |
| `AGI_PRP_02_AUDIT_REQUIRED` | true | Privileged actions need audit |
| `AGI_PRP_02_SECRET` | dev secret | Pepper for hashes / seals |

## Quality gates

Reject when authentication fails, tenant mismatches, permission missing, API key expired, session revoked, execution context invalid, or privileged audit missing.

## Invariants

- Authentication is independent of orchestration
- Authorization occurs before UAG / RW / PUB execution
- Domain engines remain unaware of users and roles
- Every privileged action creates an immutable audit event
- Tenant isolation for user-owned resources; global intelligence stays shared
- No new intelligence engines
