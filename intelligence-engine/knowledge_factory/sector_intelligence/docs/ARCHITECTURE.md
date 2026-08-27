# Institutional Sector Intelligence (ISI) — Sprint 5

**Status:** Knowledge Factory enrichment only  
**Reasoning Architecture:** Frozen v1.0  
**Does not modify:** Phases 1–7, Historical Depth  
**Version:** `institutional-sector-intelligence-v1.0.0`

## 1. Architecture

```
Knowledge Factory
  → Sector DNA + Playbooks (institutional priors)
  → Constituents from sector_map
  → Historical Depth metrics (soft read)
  → Sector Derived Producers
  → Institutional Sector Objects + Evidence Packs
  → Soft enrich existing Evidence Producers
  → Phases 1–7 unchanged
```

## 2. Folder structure

```
knowledge_factory/sector_intelligence/
  schema.py
  store.py
  dna/catalog.py
  playbooks/catalog.py          # executable institutional playbooks
  macro_map.py
  producers/core.py
  objects/compile.py
  queries.py
  pipeline.py
  dashboard.py
  docs/ARCHITECTURE.md
```

Store: `data/knowledge_factory/sectors/` (`KF_ISI_STORE_ROOT`).

## 3–6. Schemas

- **Sector DNA:** business model, sensitivities, frameworks preferred/forbidden, mental models  
- **Playbook:** value drivers, watch metrics, risks, preferred valuation, historical behaviour, checklist  
- **Historical sector:** median PE/PB/ROIC histories, percentiles, leadership rankings  
- **Institutional Sector Object:** profile + DNA + playbook + valuation + cycles + macro + frameworks + timeline + quality

## 7. Pipeline

`run_sector_intelligence_pipeline()` — compile all universe sectors, cross-sector rankings, dashboard.

## 8. Dashboard / North Star

`Institutional Sector Intelligence Coverage` — sector %, DNA completeness, historical/macro/cycle/framework/playbook coverage, evidence quality.

## 9. Acceptance tests

`tests/test_sector_intelligence.py`

## 10. Migration

1. Deploy ISI package (no Phase / HD code changes).  
2. Nightly after Historical Depth pipeline.  
3. Soft-read HD metrics; do not rewrite HD store.  
4. Next KPI: **Macro Intelligence**.
