# Company Memory — Knowledge Compiler

AGIB's persistent, company-specific institutional knowledge base.

> Do not ask the LLM to rediscover facts every time. Feed it structured historical intelligence that you have already built.

## Pipeline

```text
Ingest (NSE / P2 packs / HD)
        ↓
Normalise & version (pit_record)
        ↓
Derive intelligence objects
        ↓
CompanyMemory
        ↓
CID → Retrieval → Decision Engine
```

## CompanyMemory sections

- Price Intelligence (returns, drawdowns, volatility)
- Financial History (QoQ/YoY/TTM/CAGR, margins, ROE/ROCE, cash quality)
- Ownership History (promoter/FII/DII/MF/insurance trends)
- Valuation History (bands, peers, premium/discount)
- Corporate History (strategy themes by year)
- Event Timeline
- Sector History (living peer KPI panels)
- Risk History
- Latest Evidence

## CLI

```bash
PYTHONPATH=. python -m company_memory TCS
PYTHONPATH=. python -m company_memory --ic10
```

## APIs

- `GET /v1/company-memory/health`
- `GET /v1/company-memory/{ticker}`
- `GET /v1/company-memory-ic10`
