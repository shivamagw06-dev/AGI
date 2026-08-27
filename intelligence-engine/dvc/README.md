# DVC V1 — Data Validation & Consensus Platform

**Architecture status:** v1.0.1 LOCKED  
**Role:** Platform layer inside Market Data (not an engine, not a provider)

```
External Providers → Provider Registry → Canonical Mapper → DVC → MarketDataClient → LEO → CID → KF → IRP → Ask AGI
```

## What it does

- Multi-provider sampling with configurable priority
- Field-level audited institutional data objects (value, provider, confidence, version, history)
- Consensus engine (numeric + categorical)
- Conflict detection & severity
- Data quality scores + institutional grade gates
- Provider reliability learning
- Soft CID enrichment + Ask AGI conflict hints
- Admin dashboard at `/admin/data-quality`

## Flags

| Env | Default | Purpose |
|-----|---------|---------|
| `DVC` | `true` | Master enable |
| `DVC_MULTI_PROVIDER` | `true` | Sample all configured providers |
| `DVC_AUTO_ATTACH_CID` | `true` | Soft-merge into CID |
| `DVC_PROVIDER_PRIORITY` | _(empty)_ | Override e.g. `indianapi:2,yahoo:5` |

## Out of scope

No engine redesign. No LEO / IRP / RSP / provider redesign.
