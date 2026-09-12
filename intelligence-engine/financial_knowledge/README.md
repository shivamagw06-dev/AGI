# FKB-01 — Institutional Financial Knowledge Base

Canonical definitions for metrics, ratios, relationships, thresholds, glossary, and sector guidance.

**Spec:** [`docs/FKB_01_INSTITUTIONAL_FINANCIAL_KNOWLEDGE_BASE.md`](../../docs/FKB_01_INSTITUTIONAL_FINANCIAL_KNOWLEDGE_BASE.md)

## Layering

| Layer | Role |
| --- | --- |
| FSE | Stores facts |
| FKB | Defines what concepts mean |
| FIRE | Analyses facts using knowledge |

FKB performs **no analysis**.

## Registry

```python
from financial_knowledge import knowledge

knowledge.metric("Revenue")
knowledge.ratio("ROCE")
knowledge.relationship("PAT_OCF")
knowledge.threshold("InterestCoverage")
knowledge.glossary("Operating Leverage")
```

## CLI

```bash
python -m financial_knowledge --health
python -m financial_knowledge --metric ROCE
python -m financial_knowledge --ratio OperatingMargin
python -m financial_knowledge --relationship PAT_OCF
python -m financial_knowledge --glossary OperatingLeverage
```
