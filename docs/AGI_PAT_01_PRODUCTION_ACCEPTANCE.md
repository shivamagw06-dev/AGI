# AGIB PAT-01 — Production Acceptance Test

**Workstream:** PAT-01  
**Platform:** AGIB v1.0.0 GA (architecture frozen)  
**Role:** Break the platform before onboarding users  
**Adds intelligence engines:** No

---

## Mission

Validate that every subsystem works together under realistic conditions. This goes beyond unit tests — it is the certification gate between GA/Launch instrumentation and real-user onboarding.

```text
Try to break AGIB → certify → closed beta (5–10 analysts) → then consider v1.1
```

---

## Success criteria

| Category | Target |
| --- | ---: |
| Test cases | 200+ |
| Pass rate | 100% |
| Critical failures | 0 |
| Architecture score | 100 |
| Memory leaks | 0 |
| Security violations | 0 |

Overall label when met: **PRODUCTION CERTIFIED**

---

## Fifteen phases

1. System Boot  
2. Data Layer (coverage · freshness · duplicates · missing · hash)  
3. Knowledge Graph (Company→Sector→Industry→Macro→Portfolio)  
4. Intelligence × 50 companies (Observation · Forecast · Decision · Risk · Policy · Committee)  
5. Ask AGI × 100 questions (routing · evidence · latency · no hallucination · no BUY)  
6. Research Workspace  
7. Publishing (PDF · HTML · Markdown · JSON)  
8. Multi Portfolio (Growth · Income · Small Cap · Client A/B)  
9. Security (attacks rejected)  
10. Performance stress (10→500 users)  
11. Observability (Execution · Security · Observability contexts)  
12. RC-01 (`python -m institutional_architecture` → PASS 100)  
13. Failure injection (Redis · Postgres · Vector · Scheduler · API · Worker)  
14. End-to-end analyst workflow  
15. Long-running stability (24h · 48h · 7d contracts)

---

## Package layout

```text
intelligence-engine/institutional_acceptance/
    test_runner.py
    scenarios/
    stress/
    failure/
    workflow/
    reports/
    dashboards/
```

---

## CLI

```bash
cd intelligence-engine
PYTHONPATH=. python -m institutional_acceptance
PYTHONPATH=. python -m institutional_acceptance --quiet --mode harness
```

Harness mode (default) runs deterministic contract cases suitable for CI. Live mode soft-probes real subsystems when available; soak/failure kills remain ops-runbook items.

---

## APIs

| Method | Path |
| --- | --- |
| GET | `/v1/acceptance/health` |
| POST | `/v1/acceptance/run` |
| GET | `/v1/acceptance/report` |
| GET | `/v1/acceptance/cases` |
| GET/POST | `/v1/acceptance/phase/{phase}` |
| GET | `/v1/acceptance/diagnostics` |

Mission Control **Acceptance Center** surfaces cases, pass rate, critical failures, architecture score, security, memory leaks, and certification status.

---

## After PAT passes

Run a **closed beta with 5–10 experienced finance professionals**. Give realistic research tasks, observe hesitation and missing capabilities, and use that evidence to prioritize v1.1 — not brainstormed engines.
