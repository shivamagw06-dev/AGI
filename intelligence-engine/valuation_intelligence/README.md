# P2.2 — Valuation Intelligence

Institutional-grade **synthesis** engine. Consumes P2.6 market context, P2.1 financial statements, P2.3 ownership context, and a configurable peer registry — then produces relative valuation, historical bands, and observation-only narratives for CID / Decision Engine.

**Does not** issue BUY/SELL recommendations.  
**Does not** modify Decision Engine formulas or institutional gate thresholds.

## Pipeline

```text
Market Context (P2.6)
        │
        ▼
Financial Statements (P2.1)
        │
        ▼
Ownership (P2.3)
        │
        ▼
Peer Intelligence (registry + PIL overlay)
        │
        ▼
Valuation Intelligence (P2.2)
        │
        ▼
CID → Decision Engine
```

## APIs

- `GET /v1/valuation-intelligence/health`
- `GET /v1/valuation-intelligence/{ticker}`
- `POST /v1/valuation-intelligence`
- `GET /v1/valuation-intelligence-ic10`

## CLI

```bash
python -m valuation_intelligence TCS --max-peers 5
python -m valuation_intelligence --ic10
```

## Peer registry

Configurable in `peers.py` (`PEER_REGISTRY`). Business math never hard-codes peer lists.
