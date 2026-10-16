# KFE + KCE — Operate Layer (Sprint 6.5)

**Service:** AGI Knowledge Acquisition Platform  
**Layer:** Knowledge Freshness Engine + Knowledge Confidence Engine  
**Version:** 0.5.0  
**Part of:** Sprint 6.5 Operate (AKO + Freshness + Confidence)

---

## Objective

Finish Phase 6 so every published Knowledge Object can answer:

1. **When was I last updated?** (KFE)  
2. **How trustworthy am I?** (KCE)

This lets Ask / Intelligence Engine say:

> “My knowledge is current as of 10:32 AM IST.”

and weight evidence by confidence **before** IEW.

---

## Knowledge Freshness Engine (KFE)

### Per-object report

```yaml
Company:
  Infosys
Freshness: 37 minutes
Status: Fresh
current_as_of: "My knowledge is current as of 10:32 AM IST (28 Jul 2026)."
```

```yaml
Sector:
  Auto
Freshness: 3 days
Status: Needs Refresh
```

### Status vocabulary

| Status | Meaning |
|---|---|
| `Fresh` | Within institutional SLA |
| `Needs Refresh` | Older than SLA |
| `Missing` | No published object |
| `Unknown` | Present but timestamp unreadable |

### Responsibilities

- Evaluate age vs object-type / section SLAs  
- Persist `freshness_registry` at publish time  
- Expose portfolio health to AKO Mission Control  
- Attach freshness + `current_as_of` on KRIG bundles  

KFE does **not** collect data or trigger Ask-path acquisition.

---

## Knowledge Confidence Engine (KCE)

### Per-object report

```yaml
Financial Statement:
  Confidence: 99%
  Reasons:
    - Yahoo + NSE + Company IR agree
```

```yaml
News:
  Confidence: 58%
  Reasons:
    - Only Yahoo reported it
```

### Scoring principles

1. Primary source baseline (exchange > IR > Yahoo > derived)  
2. Multi-source agreement bonus (2 sources / 3+ sources)  
3. Filing corroboration (NSE/BSE + Company IR)  
4. Object-type priors (financials up; single-source news down)  
5. Cap at 99%; map to High / Medium / Low labels  

### Responsibilities

- Score at Knowledge Object build time  
- Persist `confidence_registry` at publish time  
- Surface confidence on KRIG bundles for IE weighting  
- Expose portfolio confidence to Mission Control  

KCE does **not** reason about investment theses — it only scores **source trust**.

---

## Integration

```text
Collectors → KO Builder (KCE score)
         → Publisher (KFE register + KCE register)
         → Knowledge Store
         → KRIG Bundle (freshness + confidence)
         → Intelligence Engine
```

AKO overnight health verifies both registries.

---

## APIs

```text
GET /v1/knowledge/freshness/{object_type}/{subject_key}
GET /v1/knowledge/confidence/{object_type}/{subject_key}
GET /v1/ako/freshness
GET /v1/ako/confidence
GET /v1/ako/mission-control   # includes freshness + confidence blocks
```

---

## Success criteria

- Every published KO has freshness registry row  
- Every published KO has confidence registry row  
- Bundles expose freshness status + current-as-of  
- Bundles expose confidence for IE evidence weighting  
- Ask never triggers collectors to “refresh on demand”  
- Mission Control shows freshness + confidence portfolio health  
