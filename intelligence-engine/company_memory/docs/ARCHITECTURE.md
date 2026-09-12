# Company Memory — Knowledge Compiler Architecture

**Version:** `company-memory-v1.0.0`  
**Role:** Persistent institutional knowledge base (not LLM training)

## Principle

Do not ask the LLM to rediscover facts every time. Ingest exchange evidence once, derive long-lived intelligence objects, version them, and expose them to CID / Decision Engine as reusable memory.

## Pipeline

```
Historical Data Pipeline / P2 packs
            │
            ▼
     Raw NSE Evidence Lake (HD series)
            │
            ▼
   Normalization & Versioning (pit_record)
            │
            ▼
     Company Knowledge Repository
            │
   ┌────────┼────────────┐
   ▼        ▼            ▼
Financial  Corporate   Market
History    History     History
   │        │            │
   └────────┼────────────┘
            ▼
     CompanyMemory object
            │
            ▼
  Retrieval + CID + Decision Engine
```

## What is derived (not raw dumps)

| Layer | Derived objects |
|---|---|
| Price | 1Y/3Y/5Y/10Y returns, drawdown, recovery, volatility |
| Financial | QoQ/YoY/TTM, CAGRs, margins, ROE/ROCE, cash quality |
| Ownership | Promoter/FII/DII/MF/insurance trends across quarters |
| Valuation | Current multiples, historical bands, peer premium/discount |
| Corporate | Year-keyed strategy themes from event ledger |
| Events | Chronological ledger (actions, filings, milestones) |
| Sector | Living peer KPI panels (CASA/NIM/… by sector) |

## What is reference-only (not permanent memory)

Trading holidays, market timings, static security master fields, ephemeral circular metadata.

## External source catalog (future)

BSE, SEBI, MCA, RBI, AMFI, CCIL, MOSPI, Company IR — see `schema.EXTERNAL_SOURCES`.

## Governance

- No BUY/SELL recommendations
- Does not modify Decision Engine formulas or gate thresholds
- Soft-attaches to CID; fail-open
