# P2.1 — Financial Statements & Earnings Intelligence (NSE XBRL)

> **Canonical warehouse architecture:** [FSE-01](../../docs/FSE_01_FINANCIAL_STATEMENTS_ENGINE.md)  
> This package is the NSE XBRL **extraction adapter** under FSE. New consumers must read financials via `financial_statements_engine`, not by bypassing to parsers.

Programme workstream **P2.1**. Same evidence-layer pattern as P2.3 Ownership:

```text
NSE Integrated Filing Index (primary)
        +
NSE Corporates Financial Results (secondary)
        │
        ▼
Quarter/Annual Resolver → XBRL → IND-AS Parser
        │
        ▼
Financial Statements Pack → Earnings Intelligence → CID → Decision Engine
```

## What this is

Correct ingestion of financial statements that already exist on NSE. **Not** a new scoring engine and **not** BUY/SELL generation.

## APIs

- `GET /v1/earnings-intelligence/health`
- `GET /v1/earnings-intelligence/{ticker}`
- `POST /v1/earnings-intelligence`

## CLI

```bash
python -m earnings_intelligence TCS --quarters 4 --annuals 2
```

## Frozen surfaces

Constitution · Governance Spec · Decision Engine formulas · Gate thresholds · Evaluation Lab · IAT · Mission Control
