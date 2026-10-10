# Institutional Evidence Retrieval Engine (IERE)

AGIB v3.2 Track 5 — retrieve the best structured institutional evidence for every question.

```
Question
  → Intent Detection
  → Entity Resolution
  → Evidence Discovery
  → Evidence Ranking (deterministic)
  → Evidence Assembly
  → Evidence Pack
  → Existing Reasoning (unchanged)
```

## Rules

- Never retrieve documents as PDFs for reasoning
- Never query raw APIs — soft-read Knowledge Factory / IDI / LIDI / RO only
- Deterministic ranking only (no LLM ranking)
- Point-in-time: `available_from <= as_of`
- Soft-wire Ask + Research Office + Mission Control
- Reasoning / governance / committees / planner frozen

## Package

```
evidence_retrieval/
  discovery/   ranking/   retrieval/   citations/
  provenance/  replay/    graph/       quality/
  dashboard/   reports/   assembly/    tests/
```

## APIs

- `GET /v1/evidence/dashboard`
- `GET /v1/evidence/search`
- `GET /v1/evidence/company/{ticker}`
- `GET /v1/evidence/document/{id}`
- `GET /v1/evidence/graph`
- `GET /v1/evidence/replay`
- `GET /v1/evidence/health`
