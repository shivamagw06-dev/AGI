# KAIP Platform Contract — Sprint 6.1

**Service:** AGI Knowledge Acquisition Platform (KAIP)  
**Version:** 0.2.0  
**Status:** Foundation (Sprint 6.1) + Institutional Knowledge Model (Sprint 6.2)  
**Boundary:** Acquisition + knowledge modeling only. No reasoning, no LLM, no embeddings, no portfolio/monitoring updates.

> Sprint 6.2 knowledge contract: [`IKO_PLATFORM_CONTRACT.md`](IKO_PLATFORM_CONTRACT.md)

---

## 1. Purpose

KAIP is a standalone, always-on service that:

1. Continuously ingests institutional data from external sources
2. Converts every payload into AGI’s canonical knowledge model
3. Publishes curated **Knowledge Objects** to the Intelligence Engine

The Intelligence Engine must never know Yahoo, NSE, BSE, or Company IR exist.

---

## 2. Pipeline contract

```text
External Sources
      │
      ▼
Acquisition Scheduler     # finance-agnostic job runner
      │
      ▼
Source Collectors         # Yahoo / NSE / BSE / Company IR only
      │
      ▼
Raw Event Store           # append-only; never overwrite
      │
      ▼
Validation & Quality Gates
      │
      ▼
Canonical Normalizer      # provider fields → AGI language
      │
      ▼
Entity Resolution         # ticker → Company + Sector + Industry + Index
      │
      ▼
Knowledge Object Builder  # five object types only
      │
      ▼
Relationship Builder      # Company → Sector → Industry → Index → Peers
      │
      ▼
Change Detection          # material deltas → Learning Events
      │
      ▼
Knowledge Publisher       # Knowledge Objects only (never raw JSON)
      │
      ▼
Intelligence Engine
```

Each stage has a stable input/output contract. Collectors, parsers, publishers, and the Intelligence Engine may evolve independently as long as they honour these contracts.

---

## 3. Collectors (Sprint 6.1 only)

| Collector ID | Interval | Source |
|---|---|---|
| `YahooCollector` | 30s | Yahoo Finance quote/profile |
| `NSEAnnouncementCollector` | 30s | NSE corporate announcements |
| `NSEBhavcopyCollector` | daily | NSE equity bhavcopy |
| `BSECorporateActionCollector` | daily | BSE corporate actions |
| `CompanyIRCollector` | daily | Company IR pages |

Collectors emit **Raw Events**. They do not normalize, resolve entities, or publish.

---

## 4. Raw Event contract

```json
{
  "event_id": "uuid",
  "source": "yahoo|nse|bse|company_ir",
  "collector_id": "YahooCollector",
  "endpoint": "https://...",
  "company_symbol": "INFY",
  "payload": {},
  "timestamp": "ISO-8601 UTC",
  "checksum": "sha256 hex"
}
```

Rules:

- Append-only. Nothing is overwritten.
- Every fetch creates a new event, even if payload is identical.
- Duplicate detection happens in validation (downstream), not by deleting raw history.

---

## 5. Validation gates

An event continues only if all pass:

1. **Schema** — required envelope fields present
2. **Required fields** — source-specific payload keys present
3. **Timestamp** — parseable UTC timestamp
4. **Duplicate detection** — same `checksum` + `source` + `company_symbol` within window is marked `duplicate` (stored, not published)
5. **Ticker validation** — symbol resolves or is creatable in entity registry
6. **Attachment validation** — URLs/attachments well-formed when present

Invalid events are recorded with `validation_status=rejected` and stop.

---

## 6. Canonical model (AGI language)

Provider fields must never leak past the normalizer.

| Provider | Provider field | AGI field |
|---|---|---|
| Yahoo | `marketCap` | `market_cap` |
| Yahoo | `trailingPE` | `pe_ratio` |
| Yahoo | `longName` | `company_name` |
| NSE | `symbol` | `company_symbol` |
| NSE | `sm_name` / announcement title | `event_title` |
| BSE | action fields | `action_type`, `ex_date`, `record_date` |

All Knowledge Objects use snake_case AGI fields only.

---

## 7. Entity resolution

Example:

```text
INFY.NS  →  Company: Infosys Ltd
            Sector: Technology
            Industry: IT Services
            Index: NIFTY50
```

Resolved entities are attached to every Knowledge Object as `entity_refs`.

---

## 8. Knowledge Objects (exactly five)

| Object type | Purpose |
|---|---|
| `CompanyProfile` | Identity, sector, industry, listing metadata |
| `MarketSnapshot` | Price, volume, valuation snapshot |
| `CorporateEvent` | Announcements / IR / calendar events |
| `CorporateAction` | Dividends, splits, bonuses, rights |
| `FinancialStatement` | Income / balance / cashflow periods |

No additional object types in Sprint 6.1.

---

## 9. Change detection → Learning Events

| Change | Behaviour |
|---|---|
| PE 24.1 → 24.2 | Ignore (immaterial) |
| Revenue growth 18% → 28% | Emit `LearningEvent` |
| New corporate action | Emit `LearningEvent` |
| Material market move (≥ threshold) | Emit `LearningEvent` |

Learning Events are first-class published objects for IE consumption. They are **not** reasoning outputs.

---

## 10. Publisher contract

Publisher emits only Knowledge Objects / Learning Events:

```json
{
  "object_type": "CompanyProfile",
  "object_id": "...",
  "company_symbol": "INFY",
  "version": 3,
  "payload": { "...canonical..." },
  "entity_refs": { "company_id": "...", "sector": "...", "industry": "...", "indexes": ["NIFTY50"] },
  "published_at": "ISO-8601 UTC",
  "source_event_ids": ["..."]
}
```

Never publish raw provider JSON. Never include provider names in object payloads (provenance may reference `source` enum for audit only).

---

## 11. Storage tables (Sprint 6.1)

```text
raw_events
knowledge_objects
company_profiles
market_snapshots
corporate_events
corporate_actions
financial_statements
learning_events
```

Keep the surface small. No vector tables. No evidence-graph tables.

---

## 12. Internal APIs only

```text
GET /v1/knowledge/company/{symbol}
GET /v1/knowledge/market/{symbol}
GET /v1/knowledge/events/{symbol}
GET /v1/knowledge/financials/{symbol}
GET /v1/knowledge/learning/{symbol}
GET /healthz
GET /readyz
```

No public endpoints. Intended consumers: Intelligence Engine and internal ops.

---

## 13. Explicit non-goals (Sprint 6.1)

Do **not** build:

- IEW / IHG / IHE integration
- Reasoning
- LLM summarisation
- Embeddings / vector search
- Evidence Graph enrichment
- Portfolio updates
- Monitoring Office updates

Those modules consume published knowledge later.

---

## 14. Success criterion

```text
Yahoo Finance updates Infosys
        → Collector detects update
        → Raw event stored
        → Validated
        → Normalized
        → Entity resolved
        → CompanyProfile updated
        → Learning event generated (if material)
        → Knowledge published
        → Intelligence Engine can retrieve updated CompanyProfile
```

---

## 15. Independence rule

| May change independently | Locked by this contract |
|---|---|
| Collector HTTP clients | Raw Event envelope |
| Yahoo/NSE endpoint paths | Canonical field names |
| Storage engine (SQLite → Postgres) | Five Knowledge Object types |
| Scheduler implementation | Internal API shapes |
| Publisher transport (HTTP/bus) | “Publish KO only, never raw” |
