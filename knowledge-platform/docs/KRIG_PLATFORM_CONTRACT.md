# Knowledge Retrieval & Intelligence Gateway (KRIG) — Sprint 6.4

**Service:** AGI Knowledge Acquisition Platform (KAIP)  
**Layer:** Knowledge Retrieval & Intelligence Gateway  
**Version:** 0.4.0  
**Depends on:** 6.1 acquisition · 6.2 IKO · 6.3 ILE  
**Boundary:** Retrieve prepared institutional knowledge for the Intelligence Engine. No reasoning. No new collectors.

---

## 1. Mission

Turn continuously learned knowledge into something the Intelligence Engine can retrieve in milliseconds.

```text
Before:  Question → Retrieve evidence → Reason
After:   Question → Knowledge Query → KRIG → Knowledge Bundle → Reason
```

The Intelligence Engine must never know Yahoo, NSE, or BSE exist.  
It only knows **knowledge**.

---

## 2. Architecture

```text
           Knowledge Store
                 │
                 ▼
       Knowledge Retrieval Gateway
                 │
   ┌─────────────┼─────────────┐
   ▼             ▼             ▼
Company API  Sector API   Market / Macro API
   ▼             ▼             ▼
 Relationship Engine & Memory
                 ▼
       Institutional Bundle
                 ▼
        Intelligence Engine
```

---

## 3. Retrieval policies

| Query type | Retrieves |
|---|---|
| **Company** | Profile, Financials, Valuation, Corporate Events, Monitoring tips, Learning Timeline, Memory, Relationships, Sector tip, Market tip |
| **Sector** | Sector object, Leaders, Valuation, Growth, Risks, Sector Learning |
| **Macro** | RBI / Inflation / GDP / Policy / Historical cycles (market-knowledge layer) |
| **Portfolio** | Thesis, Decision, Portfolio Idea, Monitoring, Learning (stubs until portfolio KOs land) |
| **Compare** | Per-company company policies + shared Sector + shared Macro + Comparison Bundle |
| **Bundle** | Explicit section list from caller |

---

## 4. Knowledge Bundle (standard object)

```yaml
KnowledgeBundle:
  query_type: company|sector|macro|portfolio|compare|bundle
  subjects: [INFY] | [technology] | [india_equity]
  company: {...}
  financials: [...]
  valuation: {...}
  corporate_events: [...]
  sector: {...}
  market: {...}
  macro: {...}
  evidence: [...]
  learning: [...]
  relationships: [...]
  monitoring: [...]
  memory: [...]
  timeline: [...]
  freshness: {...}
  cache: { hit: bool, ttl_seconds: N }
  provenance: { gateway: KRIG, version: 0.4.0 }
```

Everything downstream consumes this. Ask does not build context — KRIG delivers it.

---

## 5. Freshness Engine

| Object | Fresh SLA |
|---|---|
| Market Snapshot | 30 seconds |
| Financials | 7 days (quarterly institutional default) |
| Company Profile | 7 days |
| Corporate Events | 1 day |
| Sector Knowledge | 1 day |
| Market / Macro | 1 hour |
| Learning / Memory | 1 day |

Each section in a bundle reports:

```yaml
Financials:
  status: Fresh | Needs Refresh | Missing | Unknown
  # (status_legacy retains Stale for older consumers)
  sla: Quarterly
  updated: <ISO>
  age_seconds: N
```

KRIG records refresh hints; collectors (6.1) remain responsible for acquisition. Sprint 6.5 owns ops retries.

---

## 6. Caching

KRIG owns cache:

```text
Infosys Company Bundle → cached → TTL 5 minutes
Compare HDFCBANK|ICICIBANK → cached → TTL 5 minutes
```

If underlying knowledge versions are unchanged within TTL, reuse.

---

## 7. Internal APIs

```text
GET  /v1/knowledge/company/{ticker}     # profile (6.2) — retained
POST /v1/knowledge/bundle               # assemble by policy
GET  /v1/knowledge/bundle/company/{ticker}
GET  /v1/knowledge/sector/{sector}      # sector KO + optional bundle
GET  /v1/knowledge/market
GET  /v1/knowledge/macro
POST /v1/knowledge/compare
GET  /v1/internal/krig/metrics
```

No public endpoints.

---

## 8. Intelligence Engine contract

```text
Ask → KRIG → Knowledge Bundle → Evidence Graph / Judgment → Answer
```

IE performs **zero data discovery**. Soft-wire may attach `knowledge_bundle` onto Ask context when KRIG is reachable; degradation must not block Ask.

---

## 9. Storage

```text
knowledge_bundle_cache
retrieval_logs
freshness_registry
knowledge_dependencies
retrieval_metrics
```

---

## 10. Success criterion

Query: *Compare HDFC Bank vs ICICI Bank after RBI cut rates.*

KRIG returns a Comparison Bundle containing:

- HDFC company knowledge  
- ICICI company knowledge  
- Banking sector  
- Latest RBI / macro policy tip  
- Historical cycle tip  
- Relevant learning events  
- Corporate events  
- Valuation objects  
- Evidence / relationship links  

IE does no Yahoo/NSE discovery.

---

## 11. Non-goals

- Reasoning / judgment  
- New collectors  
- Full KOps dashboards (Sprint 6.5)  
- Public APIs  
