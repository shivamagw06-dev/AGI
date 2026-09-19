# P3.2 — Investment Knowledge Graph

Relationship intelligence façade over CompanyMemory, peer registry, ownership trends, and soft IKG seeds.

```text
CompanyMemory + Peers + Ownership + IKG soft-read
        → Investment Graph slice
        → Composite retrieval (+ Delta + CID)
        → CID enrichment (Decision Engine unchanged)
```

## CLI

```bash
PYTHONPATH=. python -m investment_knowledge_graph TCS
PYTHONPATH=. python -m investment_knowledge_graph --theme Defence
PYTHONPATH=. python -m investment_knowledge_graph --retrieve TCS
```
