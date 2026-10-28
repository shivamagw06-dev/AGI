# Institutional Learning Engine (ILE) — Sprint 6.3

**Service:** AGI Knowledge Acquisition Platform (KAIP)  
**Layer:** Institutional Learning Engine  
**Version:** 0.3.0  
**Depends on:** Sprint 6.1 (acquisition) + Sprint 6.2 (IKO)  
**Boundary:** Learn from knowledge changes. No new collectors. No LLM reasoning. No Ask UI work.

---

## 1. Purpose

Sprint 6.1 answered *where data comes from*.  
Sprint 6.2 answered *what knowledge to extract*.  
Sprint 6.3 answers:

> What changed, why it matters, what it affects, and how AGI's understanding evolves.

AGI must become **continuously smarter** — not by storing more numbers, but by producing institutional learning.

---

## 2. Pipeline

```text
New Knowledge Object
        │
        ▼
Previous Version Lookup
        │
        ▼
Change Comparator
        │
        ▼
Materiality Engine          ← Materiality Policy gates noise
        │
   significant?
   /         \
 ignore     Impact Assessment + Relationship Engine
               │
               ▼
        Learning Event Builder
               │
        ┌──────┼──────────┬────────────┐
        ▼      ▼          ▼            ▼
 Sector   Market   Contradiction   Institutional
 Learning Learning   Engine           Memory
        │
        ▼
 Learning Timeline
        │
        ▼
 Publication Envelope → Intelligence Engine
 (Company / Sector / Market / Learning / Evidence Graph / Memory)
```

---

## 3. Materiality Policy (required before learning)

Not every change becomes a Learning Event.

| Tier | Examples | Default action |
|---|---|---|
| **High** | Earnings surprises, guidance changes, major acquisitions, promoter stake changes, credit rating changes, RBI policy decisions, revenue/margin jumps beyond threshold | Always learn |
| **Medium** | Meaningful valuation shifts, analyst consensus changes, sustained sector trends, material price moves | Learn if score ≥ medium threshold |
| **Low** | Routine price ticks, minor P/E moves (24.10→24.12), small volume changes | Ignore |

Every scored change carries:

```yaml
Materiality:
  Field: Revenue Growth
  Score: 94          # 0–100
  Importance: High
  Tier: High
```

Only changes that pass the policy continue to Impact / Learning / Memory.

Full policy tables: `app/ile/policy.py` + this contract §3.

### Default numeric gates (India equity institutional defaults)

| Signal | Ignore if | Material if |
|---|---|---|
| PE absolute move | < 1.0 | ≥ 1.0 (medium), ≥ 3.0 (high) |
| Price % move | < 3% | ≥ 3% (medium), ≥ 5% (high) |
| Revenue growth (pp) | < 5 pp | ≥ 5 pp (medium), ≥ 8 pp (high) |
| PAT / EBITDA margin (pp) | < 1 pp | ≥ 1 pp (medium), ≥ 2 pp (high) |
| Debt % change | < 10% | ≥ 10% (medium), ≥ 25% (high) |
| Ownership stake (pp) | < 1 pp | ≥ 1 pp (medium), ≥ 3 pp (high) |
| New corporate action / earnings event | — | High |
| Guidance change / acquisition keywords | — | High |

---

## 4. Learning outputs

### 4.1 Learning Event

Institutional observation — not a raw delta dump:

```yaml
LearningEvent:
  Company: Infosys
  Category: Financial Performance
  Observation: Revenue acceleration exceeded previous trend.
  Evidence: Quarterly Financials
  Importance: High
  Confidence: High
  MaterialityScore: 94
  Affected: [Company, Sector, Valuation]
```

### 4.2 Sector Learning

When multiple companies in a sector show the same material pattern:

```yaml
SectorLearning:
  Sector: IT Services
  Observation: Industry-wide margin compression emerging.
  Supporting Companies: [INFY, TCS, WIPRO]
```

### 4.3 Market Learning

Cross-sector themes (rates, risk-on, etc.):

```yaml
MarketLearning:
  Theme: Lower Rates
  Beneficiaries: [Banks, Autos, Housing]
  Historical Confidence: High
```

### 4.4 Knowledge Conflict

Contradictions against prior institutional assumptions:

```yaml
KnowledgeConflict:
  Status: Needs Review
  Reason: Previous assumption invalidated.
  Previous: Margins expanding
  New: Margins declining
```

### 4.5 Institutional Memory

Reusable narrative knowledge — **not** raw metrics:

```text
Infosys has entered a stronger growth phase driven by improved
execution and operating leverage.
```

### 4.6 Learning Timeline

Ordered evolution per company:

```text
2025 → Margin Expansion
2026 → Revenue Acceleration
2026 → Dividend Increase
2027 → Guidance Reduced
```

---

## 5. Storage collections (Sprint 6.3)

```text
learning_events          # enriched (already existed; extended)
sector_learning
market_learning
relationship_changes
knowledge_conflicts
learning_timeline
institutional_memory
```

---

## 6. Success criterion

When Infosys reports earnings, **without any user asking**, AGI automatically knows:

1. Revenue accelerated  
2. Margins improved  
3. Cash flow strengthened (when present)  
4. Valuation changed (when material)  
5. IT sector updated  
6. Monitoring / learning event created  
7. Institutional memory updated  
8. Evidence graph publication flags updated  
9. Company timeline updated  
10. Intelligence Engine can retrieve all of the above via internal APIs  

---

## 7. Non-goals

- New collectors  
- LLM-written prose beyond deterministic institutional templates  
- Full Evidence Graph service (Sprint 6.4 hardens retrieval)  
- Ops dashboards / freshness SLAs (Sprint 6.5)  
- Ask UI changes  

---

## 8. Independence

Collectors and IKO shapes may evolve independently as long as:

- Every KO remains versioned  
- Materiality Policy remains the gate for Learning Events  
- Published learning never includes provider field names  
