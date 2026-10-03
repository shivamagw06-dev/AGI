# AGIB v4.0 — Research Intelligence Hub (RIH)

**Status:** Implemented in `intelligence-engine/research_intelligence_hub/`  
**Version:** 4.0.0  
**Programme short:** RIH  
**Design principle:** Users come to AGI to read research; they stay because every research note becomes an interactive gateway into the institutional intelligence graph.

---

## Objective

Redesign AGI so **Research Notes are the primary knowledge object**.

A research note is **not** a document. It is an **Intelligence Object / Hub** that automatically discovers, retrieves and links related companies, sectors, markets, macro topics, IPOs, global themes, historical context, relationships, analogues, forecasts and supporting evidence.

---

## Architecture

```text
                         Research Note (Intelligence Hub)
                                      │
     ────────────────────────────────────────────────────────
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
 Companies   Sectors    Markets    Macro     IPO / Global
     │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┘
                          │
                          ▼
                 Historical Context
                          │
                          ▼
              Relationship Intelligence
                          │
                          ▼
               Historical Analogues
                          │
                          ▼
                Forecast Intelligence
                          │
                          ▼
                Supporting Evidence
```

The note stores **references and metadata**. Latest intelligence is retrieved dynamically from AGI-owned platforms so underlying updates appear immediately in the hub.

---

## ResearchObject schema

```yaml
id / headline / publication_date / session
executive_summary / investment_thesis / key_conclusions / why_it_matters
companies[] / sectors[] / markets[] / macro_topics[]
ipo_links[] / global_topics[]
historical_context[] / relationships[] / historical_analogues[]
forecast: Bull|Base|Bear (+ probability, confidence, catalysts, risks, invalidators)
supporting_evidence[] / related_research[]
confidence / importance_score / freshness / version
```

---

## Guardrails

* AGI-owned knowledge only — `providers_queried: []`
* Ask never collects or rebuilds hubs
* No BUY/SELL, no target prices, no single-path certainty
* Soft-wires Company / Sector / Market / Macro / Relationship / Analogue / Forecast platforms
* Every evidence item is marked `traceable: true`

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/rih/health` | Programme health |
| GET | `/v1/research/hub` | List hubs |
| GET | `/v1/research/hub/{note_id}` | Full Intelligence Object |
| GET | `/v1/research/hub/{note_id}/graph` | Graph rooted at the note |
| GET | `/v1/research/hub/{note_id}/history` | Version history |
| GET | `/v1/research/hub/dashboard` | Mission Control JSON |
| POST | `/v1/research/hub/build` | Build from article metadata |
| POST | `/v1/research/hub/run` | Ops publish catalog hubs |
| GET | `/v1/admin/research-intelligence-hub` | HTML ops board |

Node proxy mirrors these under `/api/intelligence/...`.

---

## Product surface

* `ArticleView.intelligence_hub` soft-assembled in UI Aggregation
* `ArticleKnowledgePanel` renders hub navigation:
  Executive Summary → Why It Matters → Companies → Sectors → Market → Macro → Historical Context → Relationships → Analogues → Bull/Base/Bear → Evidence → Related Research

---

## LangSmith traces

```text
research_hub_ingest
research_entity_extraction
research_link_assembly
research_relationship_retrieval
research_analogue_retrieval
research_forecast_attachment
research_evidence_attachment
research_hub_publication
```

---

## Mission Control

Soft board `research_intelligence_hub` (`phase: 4.0`):

* Hub count · link coverage · current hub · primary knowledge object flag

---

## Success criteria

* Research notes are the primary entry point into AGI.
* Every article becomes a structured Intelligence Object, not static content.
* Companies, sectors, macro, markets, IPOs and global topics link automatically.
* Historical context, relationships, analogues and forecasts surface without manual work.
* Insights are evidence-backed and navigable across the platform from a single note.
