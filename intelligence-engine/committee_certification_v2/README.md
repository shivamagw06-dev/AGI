# AGIB Institutional Committee Certification (IC-10 v2.0)

Validates that AGIB behaves like an institutional research analyst after P2.6 / P2.3 / P2.1 / P2.2 — without modifying governance.

## Universe

HDFCBANK, RELIANCE, TCS, ETERNAL, **TATAMOTORS** (resolves to `TMPV`), SUNPHARMA, NTPC, HAL, ASIANPAINT, ULTRACEMCO.

## Tests

1. Evidence completeness (≥95%)
2. Sector differentiation
3. Ownership intelligence
4. Valuation intelligence
5. Financial intelligence (≥90%)
6. Decision quality
7. Governance integrity
8. Narrative quality
9. Robustness (consecutive runs)
10. Committee readiness verdicts

## CLI

```bash
PYTHONPATH=. python -m committee_certification_v2 --runs 3 --max-peers 3
```

## APIs

- `GET /v1/committee-certification-v2/health`
- `GET /v1/committee-certification-v2/run?runs=1`
- `GET /v1/committee-certification-v2/latest`
