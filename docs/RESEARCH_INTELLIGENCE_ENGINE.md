# Phase 8.4 — Research Intelligence Engine (RIE) v1.0

**Module:** `intelligence-engine/research_intelligence_engine/`  
**Admin:** `/admin/research-intelligence`  
**APIs:** `/v1/research/*` (BFF: `/api/intelligence/research/*`)

## Role

RIE turns AGIB from a valuation platform into an **institutional equity research** layer.

It answers: *What is the complete investment research case for this company?*  
It does **not** predict prices or issue BUY/SELL recommendations.

## Principles

- Consumer only — never calls Upstox / Yahoo / downloads PDFs
- No UI calculations
- Everything from Institutional Warehouse + UVE / HVIE / VARIE / VPAE / ownership intelligence
- Every section carries Observed / Derived / Inferred + confidence
- DQIV rejects unsupported conclusions and recommendation language

## Sections

Executive · Business · Financial Quality · Growth · Profitability · Capital Allocation · Valuation · Ownership · Risk · Catalysts · Monitoring · Timeline · Confidence

## Surfaces

| Surface | Integration |
| --- | --- |
| Valuation Terminal | Research tab → `ResearchDossierPanel` |
| Ask AI | KUL provider `research_intelligence_engine` |
| Admin | `/admin/research-intelligence` |
| Warehouse | `rie_company_dossier` summary tab |

## Distinct from Phase 3.4 `research_intelligence`

The older `research_intelligence` package is a question/corpus analyser.  
Phase 8.4 RIE is the **company dossier composer** over live warehouse + valuation engines.
