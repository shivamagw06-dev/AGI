# System Integration — Intelligence Stack → Main

**Branch:** `cursor/integrate-all-intelligence-4cc0`  
**Merges tip:** `cursor/research-intelligence-hub-4cc0` (Phases 8–12 + RIH v4.0) into `main`

---

## What is integrated

| Layer | Programme | Status |
|---|---|---|
| Macro | CMKP → HMIP → MRI → HMAI → MFI | In stack |
| Sector | CSKP → HSIP → SRI → HSAI → SFI | In stack |
| Market | CMKTP → HMKIP → MKRI → HMKAI → MKFI | In stack |
| Research | **RIH v4.0** — Research notes as Intelligence Hubs | In stack |

Research notes are the **primary knowledge object**. Opening one article navigates the full institutional graph.

---

## Runtime wiring

1. **CMS ingest queue** (`server/services/cmsIngestJobs.js`)
   - Stages: `queued → wake_engine → kip_ingest → knowledge_compound → research_hub → completed`
   - `research_hub` soft-calls `POST /v1/research/hub/build` (never blocks success)

2. **CMS article learning** (`server/services/cmsArticleLearning.js`)
   - After learn + KC populate, soft-builds RIH hubs for learned articles

3. **UI Aggregation**
   - `ArticleView.intelligence_hub` soft-assembled from RIH
   - `ArticleKnowledgePanel` renders hub navigation

4. **Mission Control**
   - Soft boards for RIH / MKFI / SFI / CMKTP / HMKAI
   - Architecture map includes Macro / Sector / Market / Research Hub nodes
   - Admin UI section: *Intelligence Stack · Research-Centric Graph*

5. **System inventory APIs**
   - `GET /v1/system/intelligence-stack`
   - `POST /v1/system/intelligence-stack/bootstrap` (ops only)

---

## Guardrails retained

* Ask never collects
* `providers_queried: []` on read/forecast/hub paths
* Soft-wire only — missing upstream tips degrade gracefully
* No BUY/SELL or single-path certainty

---

## Bootstrap (ops)

```bash
curl -X POST "$IE/v1/system/intelligence-stack/bootstrap" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"publish_rih": true, "publish_mkfi": true}'
```

---

## Success

* Tip stack merges cleanly onto `main`
* CMS → KIP → KC → RIH path is live
* Mission Control surfaces the research-centric stack
* Users can navigate AGI from a single research note
