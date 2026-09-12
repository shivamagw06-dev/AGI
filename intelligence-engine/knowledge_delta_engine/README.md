# P3.1 — Knowledge Delta Engine

Incremental CompanyMemory compilation. Never rebuild from scratch; never overwrite silently.

```text
Prior CompanyMemory → New Evidence → Change Detector → Knowledge Delta
        → Versioned Memory → Event Ledger → Explainability
```

## CLI

```bash
PYTHONPATH=. python -m knowledge_delta_engine TCS
PYTHONPATH=. python -m knowledge_delta_engine TCS --explain valuation
PYTHONPATH=. python -m knowledge_delta_engine TCS --versions
```
