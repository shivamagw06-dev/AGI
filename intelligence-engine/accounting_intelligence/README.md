# Accounting Intelligence Engine (ACI) V1

Primary question: **Can the financial statements be trusted?**

Soft intelligence layer — not financial-ratio reporting. Evaluates earnings quality, cash quality, accruals, revenue recognition, working capital, balance-sheet quality, policy changes, forensic models (Beneish / Piotroski / Altman), and manipulation risk.

Also includes **Accounting Behaviour** fingerprint (Conservative and Consistent, Increasingly Aggressive, etc.) that evolves with evidence.

## Pipeline position

```text
Official Filings → FIL → FDI → MII → ACI → EIL → PIL → Analysts → IC → CIO → RW → ACS → IRS → Production
```

## Flag

`ACCOUNTING_INTELLIGENCE=true`

## APIs

- `GET /v1/accounting-intelligence/company/{ticker}`
- `GET /v1/accounting-intelligence/history/{ticker}`
- `POST /v1/accounting-intelligence/analyse`
- `GET /v1/admin/accounting-intelligence`
