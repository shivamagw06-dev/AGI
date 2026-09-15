# Institutional Hypothesis Generation Engine (IHG) V1

**Programme:** RQ2 — Hypothesis Intelligence  
**Sprint:** 1  
**Architecture:** v1.0.1 LOCKED — soft-wire only; not a top-level intelligence layer

## Position in the stack

```
IREP (Research Execution Package)
        ↓
IHG (Hypothesis Generation)   ← this package
        ↓
First analyst research
```

## Primary question

> What are the most plausible explanations or investment theses that should be tested?

## Five quality rules

Every hypothesis must be:

1. **Specific**
2. **Testable**
3. **Falsifiable**
4. **Evidence Required**
5. **Decision Relevant**

Generic statements (e.g. “Apple is a good company”) are rejected.

## Package layout

```
hypothesis_engine/
├── generator/
├── taxonomy/
├── ranking/
├── evidence_map/
├── confidence/
├── assumptions/
├── contradiction_detector/
├── memory/
├── diagnostics/
├── quality_rules/
├── flags.py
├── schema.py
└── production.py
```

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/hypothesis-engine/health` | Health |
| GET | `/v1/hypothesis-engine/constitution` | Constitution |
| GET | `/v1/hypothesis-engine/dashboard` | Admin dashboard samples |
| GET | `/v1/hypothesis-engine/quality-gates` | ≥1000 scenario gates |
| POST | `/v1/hypothesis-engine/plan` | Generate hypotheses |
| POST | `/v1/hypothesis-engine/diagnostics` | Explain output |

## Admin

`/admin/hypothesis-engine`

## Ask AGI soft-slice

Attaches `hypothesis_engine` after Layer Router (and after IREP when available).
