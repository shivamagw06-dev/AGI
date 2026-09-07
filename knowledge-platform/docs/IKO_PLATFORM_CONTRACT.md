# Institutional Knowledge Objects (IKO) — Sprint 6.2

**Service:** AGI Knowledge Acquisition Platform (KAIP)  
**Layer:** Institutional Knowledge Model  
**Version:** 0.2.0  
**Depends on:** Sprint 6.1 KAIP acquisition contract  
**Boundary:** Define *what AGI learns*. No new collectors. No reasoning. No LLM.

---

## 1. Purpose

Sprint 6.1 answered:

> Where does data come from?

Sprint 6.2 answers:

> What knowledge should be extracted from that data?

AGI must stop thinking in Yahoo JSON / NSE CSV and start thinking in institutional knowledge.

---

## 2. Transformation rule

Provider payload is never stored as knowledge.

```text
Yahoo JSON
   │
   ▼
Canonical fields          (Sprint 6.1)
   │
   ▼
Institutional Knowledge Object   (Sprint 6.2)
   │
   ▼
Versioned + metadata + relationships
   │
   ▼
Learning Event (if material)
   │
   ▼
Publication envelope → Intelligence Engine
```

### Example

Yahoo returns:

```json
{
  "marketCap": 8100000000000,
  "trailingPE": 25.3,
  "revenueGrowth": 0.19,
  "sector": "Technology"
}
```

AGI publishes institutional knowledge (conceptual):

```yaml
CompanyKnowledge:
  Company: Infosys
  Valuation:
    PE: 25.3
  Business:
    Sector: Technology
  Growth:
    Revenue Growth: 19%
  Metadata:
    Source: Yahoo
    Confidence: High
    Updated: Today
    Version: 17
    Verified: true
```

---

## 3. Universal knowledge types (exactly ten)

Everything becomes one of these. No hundreds of tables.

| Type | Stores |
|---|---|
| `CompanyProfile` | Company, Business, Products, Geography, Customers, Management, Industry |
| `MarketSnapshot` | Price, Volume, Market Cap, Daily Move, 52-week range |
| `FinancialStatement` | Revenue, EBITDA, PAT, EPS, Cash, Debt, Margins |
| `CorporateEvent` | Earnings, Acquisition, Board Meeting, Guidance, Regulatory filing |
| `CorporateAction` | Dividend, Split, Bonus, Rights, Buyback |
| `Ownership` | Promoters, FIIs, DIIs, Mutual Funds |
| `AnalystConsensus` | Target Price, Recommendation, Estimate Revisions |
| `NewsEvent` | Headline, Event Type, Company, Importance |
| `SectorKnowledge` | Industry trends, Sector valuation, Leaders, Risks |
| `MarketKnowledge` | Nifty, Bank Nifty, Breadth, Market regime |

These are the universal language of AGI.

---

## 4. Versioning (never overwrite)

```text
Infosys CompanyProfile
  Version 1
  Version 2
  Version 3
  Version 4
```

Rules:

- Every accepted material/immaterial update that produces a KO creates a **new version**
- Prior versions remain queryable
- Each version records `previous_object_id`, `changed_fields`, and `change_summary`
- AGI must always be able to answer: **What changed?**

---

## 5. Metadata (required on every object)

```yaml
Source: Yahoo
Confidence: High | Medium | Low
Updated: 2026-07-28T09:30:00Z
Version: 17
Verified: true
```

| Field | Meaning |
|---|---|
| `source` | Provenance enum (`yahoo`, `nse`, `bse`, `company_ir`, `derived`) |
| `confidence` | Quality of the knowledge claim |
| `updated_at` | When this version was produced |
| `version` | Monotonic per `(object_type, subject_key)` |
| `verified` | Passed validation + entity resolution |

---

## 6. Relationships (automatic)

Every object connects into the institutional graph:

```text
Company (Infosys)
   ↓
Industry (IT Services)
   ↓
Sector (Technology)
   ↓
Index (NIFTY50)
   ↓
Peers (TCS, WIPRO, ...)
   ↓
Clients / Customers (when known)
```

No manual linking. Relationship Builder derives edges from entity resolution + KO payload.

---

## 7. Learning Events

Meaningful change creates a Learning Event — the signal Sprint 6.3 will amplify.

```yaml
LearningEvent:
  Company: Infosys
  Category: Financial
  Reason: Revenue growth accelerated
  Importance: High
  Affected:
    - Company
    - Sector
    - Valuation
```

Categories: `Financial`, `Valuation`, `Business`, `Ownership`, `Corporate`, `Market`, `Sector`, `News`  
Importance: `High`, `Medium`, `Low`

Immaterial ticks (PE 24.1 → 24.2) do **not** create Learning Events.

---

## 8. Publication envelope

After validation, publish layered knowledge (not raw feeds):

```text
Company Knowledge
        ↓
Sector Knowledge
        ↓
Market Knowledge
        ↓
Evidence Graph          (consumer in later sprint)
        ↓
Institutional Memory    (consumer in later sprint)
```

Sprint 6.2 defines the envelope and stores/publishes IKOs.  
Sprint 6.4 hardens Evidence Graph / fast retrieval.  
Ask consumes published institutional knowledge — never provider JSON.

---

## 9. Subject keys

| Object type | Subject key |
|---|---|
| Company-scoped types | `company_symbol` (e.g. `INFY`) |
| `SectorKnowledge` | `sector_key` (e.g. `technology`) |
| `MarketKnowledge` | `market_key` (e.g. `india_equity`) |
| Event/Action/News streams | subject + natural key (date/type/headline hash) |

---

## 10. Non-goals (Sprint 6.2)

- New collectors
- Institutional Learning Engine depth (Sprint 6.3)
- Evidence Graph wiring / retrieval SLAs (Sprint 6.4)
- Production ops dashboards (Sprint 6.5)
- Reasoning / LLM summarisation / embeddings

---

## 11. Success criterion

Given a Yahoo Infosys update, AGI produces versioned institutional knowledge such that:

1. No provider field names (`marketCap`, `trailingPE`) appear in published knowledge
2. Company knowledge exposes Business / Valuation / Growth in AGI language
3. Versions accumulate (v1 → v2 → …) without overwrite
4. Metadata is present on every object
5. Relationships bind Company → Industry → Sector → Index → Peers
6. Material financial change emits a Learning Event with category + affected surfaces
7. Intelligence Engine retrieves institutional knowledge via KAIP APIs
