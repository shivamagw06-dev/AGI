# IRE-02 — Deterministic Reason Composer

**Mission:** Prove AGI can explain *why* conclusions exist — not just render them.

```text
Evidence → Decision facts → Reason Composer → Institutional Reporting → Report
```

No Gemini. No GPT. No phrase bank. No LLM.

## Reason object

```python
Reason(
    title="Business Quality",
    conclusion="Strong",
    confidence=0.84,
    supporting_evidence=[...],
    supporting_points=[...],
    contradicting_points=[...],
    unknowns=[...],
)
```

Every report section is backed by exactly one `Reason`.

## Section contract (no exceptions)

Each section renders:

- Conclusion  
- Supporting Reasons  
- Contradicting Reasons  
- Unknowns  
- Evidence  
- Confidence  
- Explanation (deterministic sentences mapped from the Reason fields)

## Pipeline

1. Validate `InstitutionalReportInput`  
2. `compose_reasons()` via explanation engine (`explain_business_quality`, …)  
3. Reason Validator  
4. Render Reason → section body  
5. Quality gates + diagnostics  

## Diagnostics

Every report includes: timestamp, IRE version, reason composer version, validator version, reason object count, evidence count, quality gate PASS/FAIL.

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_reporting --ticker AXISBANK --show-reasons
```

API:

- `GET /v1/report/company/{ticker}?include_reasons=true`
- `POST /v1/report/company` with optional `include_reasons`

## Out of scope

Phrase bank, grammar/connector engines, sector language packs, random variation, LLM polish, market/portfolio/macro reports.
